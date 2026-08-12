"""Schedule sidebar APIs: suggest / list / confirm / CRUD / remind / pref."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.event_log import write_event
from app.core.models import AiJob, AppUser, ScheduleItem, Suggestion
from app.core.scope import assert_customer_in_scope
from app.features.ai import jobs as job_svc
from app.features.schedule.pipeline import run_schedule_pipeline
from app.features.schedule.remind import remind_schedule
from app.features.schedule.schemas import (
    ConfirmBody,
    CreateBody,
    PatchBody,
    PrefBody,
    RemindBody,
    SuggestBody,
)
from app.features.schedule.serializers import (
    apply_calendar_sync,
    parse_iso_dt,
    serialize_draft,
    serialize_item,
)

router = APIRouter(prefix="/sidebar/schedules", tags=["schedule"])


async def _bg_run_schedule(
    job_id: int, customer_id: int, user_id: int | None
) -> None:
    async with SessionLocal() as db:
        job = await db.get(AiJob, job_id)
        if job is None:
            return
        await run_schedule_pipeline(
            db, job=job, customer_id=customer_id, user_id=user_id
        )


@router.post("/suggest")
async def suggest_schedule(
    body: SuggestBody,
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> dict[str, Any]:
    await assert_customer_in_scope(db, user, body.customer_id)
    await job_svc.fail_stuck_jobs(
        db, customer_id=body.customer_id, task_type="schedule"
    )

    existing = (
        await db.execute(
            select(AiJob)
            .where(
                AiJob.customer_id == body.customer_id,
                AiJob.task_type == "schedule",
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
        customer_id=body.customer_id,
        task_type="schedule",
        created_by=user["id"],
        request={"force": body.force},
    )
    await db.commit()
    background.add_task(_bg_run_schedule, job.id, body.customer_id, user["id"])
    return ok({"job_id": job.id, "status": "queued"})


@router.get("/pref")
async def get_remind_pref(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    row = await db.get(AppUser, user["id"])
    if row is None:
        raise AppError(ErrorCode.NOT_FOUND, "用户不存在", http_status=404)
    return ok(dict(row.remind_pref or {}))


@router.patch("/pref")
async def patch_remind_pref(
    body: PrefBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    row = await db.get(AppUser, user["id"])
    if row is None:
        raise AppError(ErrorCode.NOT_FOUND, "用户不存在", http_status=404)
    pref = dict(row.remind_pref or {})
    pref.update(body.model_dump(exclude_unset=True))
    row.remind_pref = pref
    await write_event(
        db,
        user_id=user["id"],
        action="schedule_pref_update",
        meta={"remind_pref": pref},
    )
    await db.commit()
    return ok(pref)


@router.get("")
async def list_schedules(
    user: CurrentUser,
    db: DbSession,
    customer_id: int | None = Query(default=None),
    scope: Literal["mine", "customer"] = Query(default="mine"),
) -> dict[str, Any]:
    if scope == "customer" and customer_id is None:
        raise AppError(ErrorCode.PARAM, "scope=customer 需要 customer_id", http_status=400)

    if customer_id is not None:
        await assert_customer_in_scope(db, user, customer_id)

    q = select(ScheduleItem).where(ScheduleItem.status == "confirmed")

    if scope == "customer" and customer_id is not None:
        q = q.where(ScheduleItem.customer_id == customer_id)
        if user.get("role") != "admin":
            q = q.where(ScheduleItem.owner_user_id == user["id"])
    else:
        q = q.where(ScheduleItem.owner_user_id == user["id"])
        if customer_id is not None:
            q = q.where(ScheduleItem.customer_id == customer_id)

    q = q.order_by(ScheduleItem.start_at.nulls_last(), ScheduleItem.id.desc())
    items = (await db.execute(q)).scalars().all()

    drafts: list[Suggestion] = []
    if customer_id is not None:
        drafts = list(
            (
                await db.execute(
                    select(Suggestion)
                    .where(
                        Suggestion.customer_id == customer_id,
                        Suggestion.type == "schedule",
                        Suggestion.status.in_(("pending", "shown")),
                    )
                    .order_by(Suggestion.created_at.desc())
                )
            ).scalars().all()
        )
        for d in drafts:
            if d.status == "pending":
                d.status = "shown"
        if drafts:
            await db.commit()

    return ok(
        {
            "items": [serialize_item(i) for i in items],
            "drafts": [serialize_draft(d) for d in drafts],
        }
    )


@router.post("/confirm")
async def confirm_schedule(
    body: ConfirmBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    if not body.suggestion_id and not body.schedule_id:
        raise AppError(
            ErrorCode.PARAM, "需要 suggestion_id 或 schedule_id", http_status=400
        )

    edits = body.edits
    item: ScheduleItem | None = None

    if body.suggestion_id:
        suggestion = await db.get(Suggestion, body.suggestion_id)
        if suggestion is None or suggestion.type != "schedule":
            raise AppError(ErrorCode.NOT_FOUND, "日程建议不存在", http_status=404)
        await assert_customer_in_scope(db, user, suggestion.customer_id)
        content = dict(suggestion.content or {})
        title = (edits.title if edits and edits.title else content.get("title")) or "跟进待办"
        start_at = (
            edits.start_at
            if edits and edits.start_at is not None
            else parse_iso_dt(content.get("start_at"))
        )
        end_at = edits.end_at if edits and edits.end_at is not None else None
        priority = (
            edits.priority
            if edits and edits.priority
            else content.get("priority") or "medium"
        )
        remark = (
            edits.remark
            if edits and edits.remark is not None
            else content.get("remark") or content.get("predictive_tip")
        )
        item = ScheduleItem(
            customer_id=suggestion.customer_id,
            owner_user_id=user["id"],
            title=str(title)[:200],
            start_at=start_at,
            end_at=end_at,
            priority=priority,
            status="confirmed",
            sync_state="none",
            source="ai",
            suggestion_id=suggestion.id,
            remark=remark,
        )
        db.add(item)
        await db.flush()
        suggestion.status = "adopted"
        customer_id = suggestion.customer_id
    else:
        item = await db.get(ScheduleItem, body.schedule_id)
        if item is None:
            raise AppError(ErrorCode.NOT_FOUND, "日程不存在", http_status=404)
        if item.customer_id:
            await assert_customer_in_scope(db, user, item.customer_id)
        if user.get("role") != "admin" and item.owner_user_id != user["id"]:
            raise AppError(ErrorCode.FORBIDDEN, "无业务权限（数据范围外）", http_status=403)
        if edits:
            if edits.title is not None:
                item.title = edits.title[:200]
            if edits.start_at is not None:
                item.start_at = edits.start_at
            if edits.end_at is not None:
                item.end_at = edits.end_at
            if edits.priority is not None:
                item.priority = edits.priority
            if edits.remark is not None:
                item.remark = edits.remark
        item.status = "confirmed"
        customer_id = item.customer_id

    await apply_calendar_sync(item, body.sync_calendar)
    if item.sync_state == "synced" and not item.external_cal_id:
        item.external_cal_id = f"fake-cal-{item.id}"

    await write_event(
        db,
        user_id=user["id"],
        action="schedule_confirm",
        customer_id=customer_id,
        ref_type="schedule_item",
        ref_id=item.id,
        meta={
            "suggestion_id": body.suggestion_id,
            "sync_calendar": body.sync_calendar,
            "sync_state": item.sync_state,
        },
    )
    await db.commit()
    await db.refresh(item)
    return ok(serialize_item(item))


@router.post("")
async def create_schedule(
    body: CreateBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    await assert_customer_in_scope(db, user, body.customer_id)
    item = ScheduleItem(
        customer_id=body.customer_id,
        owner_user_id=user["id"],
        title=body.title[:200],
        start_at=body.start_at,
        end_at=body.end_at,
        priority=body.priority,
        status="confirmed",
        sync_state="none",
        source="manual",
        remark=body.remark,
    )
    db.add(item)
    await db.flush()
    await apply_calendar_sync(item, body.sync_calendar)
    if item.sync_state == "synced" and not item.external_cal_id:
        item.external_cal_id = f"fake-cal-{item.id}"
    await write_event(
        db,
        user_id=user["id"],
        action="schedule_confirm",
        customer_id=body.customer_id,
        ref_type="schedule_item",
        ref_id=item.id,
        meta={"source": "manual", "sync_state": item.sync_state},
    )
    await db.commit()
    await db.refresh(item)
    return ok(serialize_item(item))


@router.patch("/{schedule_id}")
async def patch_schedule(
    schedule_id: int,
    body: PatchBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    item = await db.get(ScheduleItem, schedule_id)
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "日程不存在", http_status=404)
    if item.customer_id:
        await assert_customer_in_scope(db, user, item.customer_id)
    if user.get("role") != "admin" and item.owner_user_id != user["id"]:
        raise AppError(ErrorCode.FORBIDDEN, "无业务权限（数据范围外）", http_status=403)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return ok(serialize_item(item))


@router.post("/{schedule_id}/remind")
async def remind(
    schedule_id: int,
    body: RemindBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    item = await db.get(ScheduleItem, schedule_id)
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "日程不存在", http_status=404)
    if item.customer_id:
        await assert_customer_in_scope(db, user, item.customer_id)
    if user.get("role") != "admin" and item.owner_user_id != user["id"]:
        raise AppError(ErrorCode.FORBIDDEN, "无业务权限（数据范围外）", http_status=403)

    result = await remind_schedule(db, item=item, user=user, mode=body.mode)
    return ok(result)
