from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.event_log import write_event
from app.core.models import AiJob, Suggestion
from app.core.scope import assert_customer_in_scope
from app.features.ai import jobs as job_svc
from app.features.reply.pipeline import run_reply_pipeline

router = APIRouter(prefix="/sidebar/reply", tags=["reply"])

FeedbackAction = Literal["copy", "adopt", "reject", "edit_adopt"]

_ACTION_STATUS = {
    "copy": "shown",
    "adopt": "adopted",
    "reject": "rejected",
    "edit_adopt": "edit_adopted",
}

_ACTION_EVENT = {
    "copy": "reply_copy",
    "adopt": "reply_adopt",
    "reject": "reply_reject",
    "edit_adopt": "reply_edit_adopt",
}


class SuggestBody(BaseModel):
    customer_id: int | None = None
    scene: str = "sales"
    force: bool = False


class FeedbackBody(BaseModel):
    suggestion_id: int
    action: FeedbackAction
    edited_content: str | None = None
    edited_text: str | None = None


def _serialize_reply(row: Suggestion) -> dict[str, Any]:
    content = row.content or {}
    return {
        "suggestion_id": row.id,
        "scene": row.scene,
        "stage": content.get("stage"),
        "primary": content.get("primary"),
        "alternatives": content.get("alternatives") or [],
        "based_on_asr": content.get("based_on_asr"),
        "status": row.status,
        "label": "AI 建议",
        "created_at": row.created_at.isoformat() + "Z" if row.created_at else None,
    }


async def _resolve_customer_id(
    db: DbSession, user: dict[str, Any], customer_id: int | None
) -> int:
    cid = customer_id or user.get("customer_id")
    if cid is None:
        raise AppError(ErrorCode.PARAM, "缺少 customer_id", http_status=400)
    await assert_customer_in_scope(db, user, int(cid))
    return int(cid)


async def _bg_run_reply(
    job_id: int, customer_id: int, scene: str, user_id: int | None
) -> None:
    async with SessionLocal() as db:
        job = await db.get(AiJob, job_id)
        if job is None:
            return
        await run_reply_pipeline(
            db, job=job, customer_id=customer_id, scene=scene, user_id=user_id
        )


@router.post("/suggest")
async def suggest_reply(
    body: SuggestBody,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> dict[str, Any]:
    cid = await _resolve_customer_id(db, user, body.customer_id)
    scene = body.scene or "sales"

    await job_svc.fail_stuck_jobs(db, customer_id=cid, task_type="reply")

    existing = (
        await db.execute(
            select(AiJob)
            .where(
                AiJob.customer_id == cid,
                AiJob.task_type == "reply",
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
        task_type="reply",
        created_by=user["id"],
        request={"scene": scene, "force": body.force},
    )
    await db.commit()
    background.add_task(_bg_run_reply, job.id, cid, scene, user["id"])
    return ok({"job_id": job.id, "status": "queued"})


@router.get("/latest")
async def latest_reply(
    user: CurrentUser,
    db: DbSession,
    customer_id: int | None = Query(default=None),
    scene: str | None = Query(default="sales"),
) -> dict[str, Any]:
    cid = await _resolve_customer_id(db, user, customer_id)
    q = (
        select(Suggestion)
        .where(
            Suggestion.customer_id == cid,
            Suggestion.type == "reply",
            Suggestion.status.in_(("pending", "shown")),
        )
        .order_by(Suggestion.created_at.desc())
        .limit(1)
    )
    if scene:
        q = q.where(Suggestion.scene == scene)
    row = (await db.execute(q)).scalar_one_or_none()
    if row is None:
        return ok(None)
    if row.status == "pending":
        row.status = "shown"
        await db.commit()
        await db.refresh(row)
    return ok(_serialize_reply(row))


@router.post("/feedback")
async def reply_feedback(
    body: FeedbackBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    row = await db.get(Suggestion, body.suggestion_id)
    if row is None or row.type != "reply":
        raise AppError(ErrorCode.NOT_FOUND, "建议不存在", http_status=404)
    await assert_customer_in_scope(db, user, row.customer_id)

    edited = body.edited_content or body.edited_text
    if body.action == "edit_adopt" and not edited:
        raise AppError(ErrorCode.PARAM, "edit_adopt 需要 edited_content", http_status=400)

    row.status = _ACTION_STATUS[body.action]
    if body.action == "edit_adopt" and edited:
        content = dict(row.content or {})
        content["edited"] = edited
        row.content = content

    await write_event(
        db,
        user_id=user["id"],
        action=_ACTION_EVENT[body.action],
        customer_id=row.customer_id,
        ref_type="suggestion",
        ref_id=row.id,
        meta={"action": body.action, "scene": row.scene},
    )
    await db.commit()
    return ok({"suggestion_id": row.id, "status": row.status})
