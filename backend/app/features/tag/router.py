"""侧边栏客户标签 API：列表/增删标签、触发 AI 推荐与确认应用。"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.event_log import write_event
from app.core.models import AiJob, CustomerTag, Suggestion, TagDef
from app.core.scope import assert_customer_in_scope
from app.features.ai import jobs as job_svc
from app.features.tag.pipeline import run_tag_recommend_pipeline

router = APIRouter(prefix="/sidebar/tags", tags=["tag"])


class AddTagBody(BaseModel):
    """手动为客户添加标签的请求体。"""

    customer_id: int
    tag_id: int


class CustomTagBody(BaseModel):
    """侧栏快捷新建标签并挂到客户。"""

    customer_id: int
    name: str
    description: str | None = None
    sop_text: str | None = None


class RecommendBody(BaseModel):
    """触发标签 AI 推荐的请求体。"""

    customer_id: int | None = None
    force: bool = False


class ConfirmRecommendBody(BaseModel):
    """确认标签推荐：可选择应用新增/移除，或指定子集。"""

    suggestion_id: int
    apply_add: bool = True
    apply_remove: bool = True
    add_tag_ids: list[int] | None = None
    remove_tag_names: list[str] | None = None


async def _resolve_customer_id(
    db: DbSession, user: dict[str, Any], customer_id: int | None
) -> int:
    """解析客户 ID 并校验当前用户可见范围。"""
    cid = customer_id or user.get("customer_id")
    if cid is None:
        raise AppError(ErrorCode.PARAM, "缺少 customer_id", http_status=400)
    await assert_customer_in_scope(db, user, int(cid))
    return int(cid)


async def _bg_run_tag_recommend(
    job_id: int, customer_id: int, user_id: int | None
) -> None:
    """后台任务：打开独立会话执行标签推荐流水线。"""
    async with SessionLocal() as db:
        job = await db.get(AiJob, job_id)
        if job is None:
            return
        await run_tag_recommend_pipeline(
            db, job=job, customer_id=customer_id, user_id=user_id
        )


def _serialize_recommendations(row: Suggestion | None) -> dict[str, Any] | None:
    """序列化标签推荐 Suggestion（add/remove 列表）。"""
    if row is None:
        return None
    content = row.content or {}
    return {
        "suggestion_id": row.id,
        "status": row.status,
        "add": content.get("add") or [],
        "remove": content.get("remove") or [],
    }


@router.get("")
async def list_sidebar_tags(
    user: CurrentUser,
    db: DbSession,
    customer_id: int | None = Query(default=None),
) -> dict[str, Any]:
    """列出客户当前标签，以及最新未处理完的标签推荐。"""
    cid = await _resolve_customer_id(db, user, customer_id)

    rows = (
        await db.execute(
            select(CustomerTag, TagDef)
            .join(TagDef, TagDef.id == CustomerTag.tag_id)
            .where(CustomerTag.customer_id == int(cid), TagDef.deleted_at.is_(None))
        )
    ).all()

    active = [
        {
            "id": tag.id,
            "customer_tag_id": ct.id,
            "name": tag.name,
            "sop_text": tag.sop_text,
            "description": tag.description,
            "source": ct.source or "manual",
        }
        for ct, tag in rows
    ]

    suggestion = (
        await db.execute(
            select(Suggestion)
            .where(
                Suggestion.customer_id == int(cid),
                Suggestion.type == "tag",
                Suggestion.status.in_(("pending", "shown")),
            )
            .order_by(Suggestion.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # 首次展示推荐时 pending → shown
    if suggestion and suggestion.status == "pending":
        suggestion.status = "shown"
        await db.commit()
        await db.refresh(suggestion)

    return ok(
        {
            "active": active,
            "recommendations": _serialize_recommendations(suggestion),
        }
    )


@router.get("/catalog")
async def list_tag_catalog(
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """启用中的标签词表（顾问侧栏点选，不依赖 /admin/tags）。"""
    _ = user  # 鉴权由 CurrentUser 完成
    rows = (
        await db.execute(
            select(TagDef)
            .where(
                TagDef.deleted_at.is_(None),
                TagDef.enabled.is_(True),
            )
            .order_by(TagDef.sort_order, TagDef.id)
        )
    ).scalars().all()
    return ok(
        {
            "items": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "sop_text": t.sop_text,
                }
                for t in rows
            ]
        }
    )


@router.post("")
async def add_sidebar_tag(
    body: AddTagBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """手动添加客户标签；已存在则幂等返回 created=False。"""
    await assert_customer_in_scope(db, user, body.customer_id)
    tag = await db.get(TagDef, body.tag_id)
    if tag is None or tag.deleted_at is not None or not tag.enabled:
        raise AppError(ErrorCode.NOT_FOUND, "标签不存在或未启用", http_status=404)

    existing = (
        await db.execute(
            select(CustomerTag).where(
                CustomerTag.customer_id == body.customer_id,
                CustomerTag.tag_id == body.tag_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return ok({"id": existing.id, "created": False, "tag_id": body.tag_id})

    row = CustomerTag(
        customer_id=body.customer_id,
        tag_id=body.tag_id,
        source="manual",
        created_by=user["id"],
    )
    db.add(row)
    await db.flush()
    await write_event(
        db,
        user_id=user["id"],
        action="tag_manual_add",
        customer_id=body.customer_id,
        ref_type="customer_tag",
        ref_id=row.id,
        meta={"tag_id": body.tag_id, "tag_name": tag.name},
    )
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id, "created": True, "tag_id": body.tag_id})


@router.post("/custom")
async def create_custom_tag_and_attach(
    body: CustomTagBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """侧栏快捷新建标签定义（若同名已存在则复用）并挂到当前客户。"""
    await assert_customer_in_scope(db, user, body.customer_id)
    name = (body.name or "").strip()
    if not name:
        raise AppError(ErrorCode.PARAM, "标签名不能为空", http_status=400)
    if len(name) > 64:
        raise AppError(ErrorCode.PARAM, "标签名过长", http_status=400)

    existing_def = (
        await db.execute(
            select(TagDef).where(TagDef.name == name, TagDef.deleted_at.is_(None))
        )
    ).scalar_one_or_none()

    created_def = False
    if existing_def is None:
        existing_def = TagDef(
            name=name,
            description=(body.description or "").strip() or None,
            sop_text=(body.sop_text or "").strip() or None,
            enabled=True,
            is_measurable=True,
            sort_order=0,
        )
        db.add(existing_def)
        await db.flush()
        created_def = True
        await write_event(
            db,
            user_id=user["id"],
            action="tag_custom_create",
            customer_id=body.customer_id,
            ref_type="tag_def",
            ref_id=existing_def.id,
            meta={"name": name},
        )
    else:
        if not existing_def.enabled:
            raise AppError(
                ErrorCode.CONFLICT, "同名标签已停用，请在后台启用后再添加", http_status=409
            )

    link = (
        await db.execute(
            select(CustomerTag).where(
                CustomerTag.customer_id == body.customer_id,
                CustomerTag.tag_id == existing_def.id,
            )
        )
    ).scalar_one_or_none()
    attached = False
    customer_tag_id = link.id if link else None
    if link is None:
        row = CustomerTag(
            customer_id=body.customer_id,
            tag_id=existing_def.id,
            source="manual",
            created_by=user["id"],
        )
        db.add(row)
        await db.flush()
        customer_tag_id = row.id
        attached = True
        await write_event(
            db,
            user_id=user["id"],
            action="tag_manual_add",
            customer_id=body.customer_id,
            ref_type="customer_tag",
            ref_id=row.id,
            meta={"tag_id": existing_def.id, "tag_name": existing_def.name, "via": "custom"},
        )

    await db.commit()
    return ok(
        {
            "tag_id": existing_def.id,
            "customer_tag_id": customer_tag_id,
            "name": existing_def.name,
            "created_def": created_def,
            "attached": attached,
        }
    )


@router.delete("/{customer_tag_id}")
async def remove_sidebar_tag(
    customer_tag_id: int,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """删除客户标签关联（按 customer_tag 主键）。"""
    row = await db.get(CustomerTag, customer_tag_id)
    if row is None:
        raise AppError(ErrorCode.NOT_FOUND, "客户标签不存在", http_status=404)
    await assert_customer_in_scope(db, user, row.customer_id)
    await write_event(
        db,
        user_id=user["id"],
        action="tag_manual_remove",
        customer_id=row.customer_id,
        ref_type="customer_tag",
        ref_id=customer_tag_id,
        meta={"tag_id": row.tag_id},
    )
    await db.delete(row)
    await db.commit()
    return ok({"deleted": True})


@router.post("/recommend")
async def recommend_tags(
    body: RecommendBody,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> dict[str, Any]:
    """触发 AI 标签推荐；已有进行中任务且未 force 时复用既有 job。"""
    cid = await _resolve_customer_id(db, user, body.customer_id)
    await job_svc.fail_stuck_jobs(db, customer_id=cid, task_type="tag_recommend")

    existing = (
        await db.execute(
            select(AiJob)
            .where(
                AiJob.customer_id == cid,
                AiJob.task_type == "tag_recommend",
                AiJob.status.in_(("queued", "running")),
            )
            .order_by(AiJob.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if existing and not body.force:
        return ok({"job_id": existing.id, "status": existing.status})

    job = await job_svc.create_job(
        db,
        customer_id=cid,
        task_type="tag_recommend",
        created_by=user["id"],
        request={"force": body.force},
    )
    await db.commit()
    background.add_task(_bg_run_tag_recommend, job.id, cid, user["id"])
    return ok({"job_id": job.id, "status": "queued"})


@router.post("/recommend/confirm")
async def confirm_tag_recommend(
    body: ConfirmRecommendBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """确认标签推荐：按开关应用新增/移除，或双关视为拒绝。"""
    suggestion = await db.get(Suggestion, body.suggestion_id)
    if suggestion is None or suggestion.type != "tag":
        raise AppError(ErrorCode.NOT_FOUND, "标签建议不存在", http_status=404)
    await assert_customer_in_scope(db, user, suggestion.customer_id)

    if suggestion.status not in ("pending", "shown"):
        raise AppError(ErrorCode.CONFLICT, "建议已处理", http_status=409)

    content = suggestion.content or {}
    added: list[str] = []
    removed: list[str] = []

    if body.apply_add:
        add_items = content.get("add") or []
        name_to_id = {
            t.name: t.id
            for t in (
                await db.execute(
                    select(TagDef).where(
                        TagDef.deleted_at.is_(None), TagDef.enabled.is_(True)
                    )
                )
            ).scalars().all()
        }
        # 可指定 add_tag_ids 子集；否则按推荐中的 tag_name 映射
        if body.add_tag_ids is not None:
            target_ids = set(body.add_tag_ids)
        else:
            target_ids = {
                name_to_id[item["tag_name"]]
                for item in add_items
                if isinstance(item, dict)
                and item.get("tag_name") in name_to_id
            }

        for tag_id in target_ids:
            tag = await db.get(TagDef, tag_id)
            if tag is None or tag.deleted_at is not None or not tag.enabled:
                continue
            existing = (
                await db.execute(
                    select(CustomerTag).where(
                        CustomerTag.customer_id == suggestion.customer_id,
                        CustomerTag.tag_id == tag_id,
                    )
                )
            ).scalar_one_or_none()
            if existing:
                continue
            db.add(
                CustomerTag(
                    customer_id=suggestion.customer_id,
                    tag_id=tag_id,
                    source="ai",
                    created_by=user["id"],
                )
            )
            added.append(tag.name)

    if body.apply_remove:
        if body.remove_tag_names is not None:
            remove_names = set(body.remove_tag_names)
        else:
            remove_names = {
                item["tag_name"]
                for item in (content.get("remove") or [])
                if isinstance(item, dict) and item.get("tag_name")
            }
        if remove_names:
            rows = (
                await db.execute(
                    select(CustomerTag, TagDef)
                    .join(TagDef, TagDef.id == CustomerTag.tag_id)
                    .where(
                        CustomerTag.customer_id == suggestion.customer_id,
                        TagDef.name.in_(list(remove_names)),
                    )
                )
            ).all()
            for ct, tag in rows:
                await db.delete(ct)
                removed.append(tag.name)

    # 增删都关闭视为拒绝推荐
    if not body.apply_add and not body.apply_remove:
        suggestion.status = "rejected"
        event_action = "tag_recommend_reject"
    else:
        suggestion.status = "adopted"
        event_action = "tag_recommend_confirm"

    await write_event(
        db,
        user_id=user["id"],
        action=event_action,
        customer_id=suggestion.customer_id,
        ref_type="suggestion",
        ref_id=suggestion.id,
        meta={"added": added, "removed": removed},
    )
    await db.commit()
    return ok(
        {
            "suggestion_id": suggestion.id,
            "status": suggestion.status,
            "added": added,
            "removed": removed,
        }
    )
