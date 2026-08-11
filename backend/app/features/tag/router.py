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
    customer_id: int
    tag_id: int


class RecommendBody(BaseModel):
    customer_id: int | None = None
    force: bool = False


class ConfirmRecommendBody(BaseModel):
    suggestion_id: int
    apply_add: bool = True
    apply_remove: bool = True
    add_tag_ids: list[int] | None = None
    remove_tag_names: list[str] | None = None


async def _resolve_customer_id(
    db: DbSession, user: dict[str, Any], customer_id: int | None
) -> int:
    cid = customer_id or user.get("customer_id")
    if cid is None:
        raise AppError(ErrorCode.PARAM, "缺少 customer_id", http_status=400)
    await assert_customer_in_scope(db, user, int(cid))
    return int(cid)


async def _bg_run_tag_recommend(
    job_id: int, customer_id: int, user_id: int | None
) -> None:
    async with SessionLocal() as db:
        job = await db.get(AiJob, job_id)
        if job is None:
            return
        await run_tag_recommend_pipeline(
            db, job=job, customer_id=customer_id, user_id=user_id
        )


def _serialize_recommendations(row: Suggestion | None) -> dict[str, Any] | None:
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


@router.post("")
async def add_sidebar_tag(
    body: AddTagBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
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
        return ok({"id": existing.id, "created": False})

    row = CustomerTag(
        customer_id=body.customer_id,
        tag_id=body.tag_id,
        source="manual",
        created_by=user["id"],
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id, "created": True})


@router.delete("/{customer_tag_id}")
async def remove_sidebar_tag(
    customer_tag_id: int,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    row = await db.get(CustomerTag, customer_tag_id)
    if row is None:
        raise AppError(ErrorCode.NOT_FOUND, "客户标签不存在", http_status=404)
    await assert_customer_in_scope(db, user, row.customer_id)
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
