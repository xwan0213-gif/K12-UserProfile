"""侧边栏客户画像 API：查询已确认画像/草稿、触发 AI 生成、编辑草稿与确认合并。"""

from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.event_log import write_event
from app.core.models import AiJob, CustomerProfile, ProfileDraft
from app.core.scope import assert_customer_in_scope
from app.core.timeutil import utcnow_naive
from app.features.ai import jobs as job_svc
from app.features.profile.pipeline import run_profile_pipeline
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter(prefix="/sidebar/profile", tags=["profile"])

ProfileField = Literal["basic_info", "study_info", "prefer_info", "timeline"]


class GenerateBody(BaseModel):
    """触发生成画像草稿的请求体。"""

    customer_id: int | None = None
    force: bool = False


class PatchDraftBody(BaseModel):
    """局部修改草稿某一字段的请求体。"""

    draft_id: int
    field: ProfileField
    value: Any


class ConfirmBody(BaseModel):
    """确认/丢弃草稿的请求体。"""

    draft_id: int
    mode: Literal["fields", "all", "discard"]
    fields: list[ProfileField] = Field(default_factory=list)


def _serialize_confirmed(row: CustomerProfile | None) -> dict[str, Any] | None:
    """将已确认画像序列化为前端可用结构。"""
    if row is None:
        return None
    return {
        "version": row.version,
        "basic_info": row.basic_info,
        "study_info": row.study_info,
        "prefer_info": row.prefer_info,
        "timeline": row.timeline,
        "sources": row.sources,
        "confirmed_at": row.confirmed_at.isoformat() + "Z" if row.confirmed_at else None,
    }


def _serialize_draft(row: ProfileDraft | None) -> dict[str, Any] | None:
    """将画像草稿序列化为前端可用结构。"""
    if row is None:
        return None
    return {
        "id": row.id,
        "confidence": float(row.confidence) if row.confidence is not None else None,
        "sources": row.sources,
        "field_status": row.field_status,
        "basic_info": row.basic_info,
        "study_info": row.study_info,
        "prefer_info": row.prefer_info,
        "timeline": row.timeline,
        "status": row.status,
        "created_at": row.created_at.isoformat() + "Z" if row.created_at else None,
    }


async def _resolve_customer_id(
    db: DbSession, user: dict[str, Any], customer_id: int | None
) -> int:
    """解析客户 ID：优先请求参数，否则取当前用户上下文，并校验可见范围。"""
    cid = customer_id or user.get("customer_id")
    if cid is None:
        raise AppError(ErrorCode.PARAM, "缺少 customer_id", http_status=400)
    await assert_customer_in_scope(db, user, int(cid))
    return int(cid)


async def _bg_run_profile(job_id: int, customer_id: int, user_id: int | None) -> None:
    """后台任务：打开独立会话执行画像生成流水线。"""
    async with SessionLocal() as db:
        job = await db.get(AiJob, job_id)
        if job is None:
            return
        await run_profile_pipeline(
            db, job=job, customer_id=customer_id, user_id=user_id
        )


@router.get("")
async def get_profile(
    user: CurrentUser,
    db: DbSession,
    customer_id: int | None = Query(default=None),
) -> dict[str, Any]:
    """查询客户已确认画像、最新草稿，以及是否正在生成。"""
    cid = await _resolve_customer_id(db, user, customer_id)

    confirmed = (
        await db.execute(
            select(CustomerProfile).where(CustomerProfile.customer_id == cid)
        )
    ).scalar_one_or_none()

    # 可继续编辑/确认的草稿：draft 与 partial_confirmed
    draft = (
        await db.execute(
            select(ProfileDraft)
            .where(
                ProfileDraft.customer_id == cid,
                ProfileDraft.status.in_(("draft", "partial_confirmed")),
            )
            .order_by(ProfileDraft.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    running = (
        await db.execute(
            select(AiJob)
            .where(
                AiJob.customer_id == cid,
                AiJob.task_type == "profile",
                AiJob.status.in_(("queued", "running")),
            )
            .order_by(AiJob.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return ok(
        {
            "confirmed": _serialize_confirmed(confirmed),
            "draft": _serialize_draft(draft),
            "generating": running is not None,
            "job_id": running.id if running else None,
        }
    )


@router.post("/generate")
async def generate_profile(
    body: GenerateBody,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> dict[str, Any]:
    """触发 AI 生成画像草稿；已有排队/运行中任务且未 force 时直接复用。"""
    cid = await _resolve_customer_id(db, user, body.customer_id)

    existing = (
        await db.execute(
            select(AiJob)
            .where(
                AiJob.customer_id == cid,
                AiJob.task_type == "profile",
                AiJob.status.in_(("queued", "running")),
            )
            .order_by(AiJob.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # 避免并发重复生成；force=True 时强制新建任务
    if existing and not body.force:
        return ok({"job_id": existing.id, "status": existing.status})

    job = await job_svc.create_job(
        db,
        customer_id=cid,
        task_type="profile",
        created_by=user["id"],
        request={"force": body.force},
    )
    await db.commit()
    background.add_task(_bg_run_profile, job.id, cid, user["id"])
    return ok({"job_id": job.id, "status": "queued"})


@router.patch("/draft")
async def patch_draft(
    body: PatchDraftBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """人工编辑草稿指定字段，并将该字段状态标记为 draft。"""
    draft = await db.get(ProfileDraft, body.draft_id)
    # 部分确认后仍允许改未确认字段
    if draft is None or draft.status not in ("draft", "partial_confirmed"):
        raise AppError(ErrorCode.NOT_FOUND, "草稿不存在或已失效", http_status=404)
    await assert_customer_in_scope(db, user, draft.customer_id)

    setattr(draft, body.field, body.value)
    status_map = dict(draft.field_status or {})
    status_map[body.field] = "draft"
    draft.field_status = status_map
    draft.created_by = "manual"
    await db.flush()
    await db.commit()
    return ok(_serialize_draft(draft))


@router.post("/confirm")
async def confirm_profile(
    body: ConfirmBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """确认草稿：可丢弃、全量合并或按字段部分合并到已确认画像。"""
    draft = await db.get(ProfileDraft, body.draft_id)
    if draft is None:
        raise AppError(ErrorCode.NOT_FOUND, "草稿不存在", http_status=404)
    if draft.status not in ("draft", "partial_confirmed"):
        raise AppError(ErrorCode.CONFLICT, "草稿状态冲突", http_status=409)
    await assert_customer_in_scope(db, user, draft.customer_id)

    if body.mode == "discard":
        draft.status = "discarded"
        await write_event(
            db,
            user_id=user["id"],
            action="profile_discard_draft",
            customer_id=draft.customer_id,
            ref_type="profile_draft",
            ref_id=draft.id,
        )
        await db.commit()
        return ok({"profile_version": None, "draft_status": "discarded"})

    fields: list[str]
    if body.mode == "all":
        fields = ["basic_info", "study_info", "prefer_info", "timeline"]
    else:
        fields = list(body.fields)
        if not fields:
            raise AppError(ErrorCode.PARAM, "fields 不能为空", http_status=400)

    profile = (
        await db.execute(
            select(CustomerProfile).where(
                CustomerProfile.customer_id == draft.customer_id
            )
        )
    ).scalar_one_or_none()

    if profile is None:
        profile = CustomerProfile(customer_id=draft.customer_id)
        db.add(profile)
        await db.flush()

    # 规范化 field_status，避免历史草稿缺 key 导致误判
    status_map = {
        "basic_info": "draft",
        "study_info": "draft",
        "prefer_info": "draft",
        "timeline": "draft",
        **dict(draft.field_status or {}),
    }

    # 仅合并本次提交的字段，绝不隐式全量写入
    for field in fields:
        setattr(profile, field, getattr(draft, field))
        status_map[field] = "confirmed"

    draft.field_status = status_map
    flag_modified(draft, "field_status")

    profile.sources = draft.sources or []
    # 首次确认为 v1，之后每次确认版本号 +1
    if profile.confirmed_at is None:
        profile.version = 1
    else:
        profile.version = int(profile.version or 0) + 1
    profile.confirmed_by = user["id"]
    profile.confirmed_at = utcnow_naive()

    all_fields = ("basic_info", "study_info", "prefer_info", "timeline")
    all_confirmed = all(status_map.get(f) == "confirmed" for f in all_fields)

    # mode=all 或四区都已确认 → merged；单区确认保持 partial_confirmed
    if body.mode == "all" or all_confirmed:
        draft.status = "merged"
        action = "profile_confirm_all"
    else:
        draft.status = "partial_confirmed"
        action = "profile_confirm_field"

    await write_event(
        db,
        user_id=user["id"],
        action=action,
        customer_id=draft.customer_id,
        ref_type="profile_draft",
        ref_id=draft.id,
        meta={"fields": fields, "mode": body.mode, "field_status": status_map},
    )
    await db.commit()
    return ok(
        {
            "profile_version": profile.version,
            "draft_status": draft.status,
            "confirmed_fields": fields,
            "field_status": status_map,
        }
    )
