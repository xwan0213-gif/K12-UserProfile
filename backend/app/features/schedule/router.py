"""Schedule sidebar APIs: suggest / list / confirm / CRUD / remind / pref."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.event_log import write_event
from app.core.models import AiJob, AppUser, ScheduleItem, Suggestion
from app.core.scope import assert_customer_in_scope
from app.core.sse import sse_hub
from app.features.ai import jobs as job_svc
from app.features.schedule.calendar import sync_to_wecom_calendar
from app.features.schedule.pipeline import run_schedule_pipeline

router = APIRouter(prefix="/sidebar/schedules", tags=["schedule"])

Priority = Literal["high", "medium", "low"]
ScheduleStatus = Literal["draft", "confirmed", "done", "cancelled"]


class SuggestBody(BaseModel):
    customer_id: int
    force: bool = False


class ScheduleEdits(BaseModel):
    title: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: Priority | None = None
    remark: str | None = None


class ConfirmBody(BaseModel):
    suggestion_id: int | None = None
    schedule_id: int | None = None
    sync_calendar: bool = False
    edits: ScheduleEdits | None = None


class CreateBody(BaseModel):
    customer_id: int
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: Priority = "medium"
    remark: str | None = None
    sync_calendar: bool = False


class PatchBody(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: Priority | None = None
    status: ScheduleStatus | None = None
    remark: str | None = None


class PrefBody(BaseModel):
    weak_tip: bool | None = None
    strong_notify: bool | None = None
    quiet_hours: list[str] | None = None

    model_config = {"extra": "allow"}


class RemindBody(BaseModel):
    mode: Literal["weak", "strong"]


def _serialize_item(row: ScheduleItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "owner_user_id": row.owner_user_id,
        "title": row.title,
        "start_at": row.start_at.isoformat() + "Z" if row.start_at else None,
        "end_at": row.end_at.isoformat() + "Z" if row.end_at else None,
        "priority": row.priority,
        "status": row.status,
        "sync_state": row.sync_state,
        "external_cal_id": row.external_cal_id,
        "source": row.source,
        "suggestion_id": row.suggestion_id,
        "remark": row.remark,
        "created_at": row.created_at.isoformat() + "Z" if row.created_at else None,
    }


def _serialize_draft(row: Suggestion) -> dict[str, Any]:
    content = row.content or {}
    return {
        "suggestion_id": row.id,
        "title": content.get("title"),
        "time_text": content.get("time_text"),
        "start_at": content.get("start_at"),
        "priority": content.get("priority"),
        "source_quote": content.get("source_quote"),
        "predictive_tip": content.get("predictive_tip"),
        "status": row.status,
        "created_at": row.created_at.isoformat() + "Z" if row.created_at else None,
    }


def _parse_iso_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            return None
    return None


async def _apply_calendar_sync(item: ScheduleItem, sync_calendar: bool) -> None:
    if not sync_calendar:
        item.sync_state = "none"
        return
    item.sync_state = "pending"
    ok_sync, _reason = await sync_to_wecom_calendar(item)
    if ok_sync:
        item.sync_state = "synced"
        item.external_cal_id = item.external_cal_id or f"fake-cal-{item.id or 'new'}"
    else:
        item.sync_state = "failed"


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
    pref = dict(row.remind_pref or {})
    return ok(pref)


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
    data = body.model_dump(exclude_unset=True)
    pref.update(data)
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
            "items": [_serialize_item(i) for i in items],
            "drafts": [_serialize_draft(d) for d in drafts],
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
            else _parse_iso_dt(content.get("start_at"))
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

    await _apply_calendar_sync(item, body.sync_calendar)
    # If sync claimed success path with fake id after flush
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
    return ok(_serialize_item(item))


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
    await _apply_calendar_sync(item, body.sync_calendar)
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
    return ok(_serialize_item(item))


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

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return ok(_serialize_item(item))


@router.post("/{schedule_id}/remind")
async def remind_schedule(
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

    owner = await db.get(AppUser, user["id"])
    pref = dict(owner.remind_pref or {}) if owner else {}
    channel_id = item.customer_id or user["id"]
    tip_text = f"{item.title}" + (
        f" · {item.start_at.isoformat()}" if item.start_at else ""
    )

    if body.mode == "weak":
        weak_enabled = pref.get("weak_tip", True)
        if weak_enabled is False:
            await write_event(
                db,
                user_id=user["id"],
                action="schedule_remind_weak",
                customer_id=item.customer_id,
                ref_type="schedule_item",
                ref_id=item.id,
                meta={"delivered": False, "reason": "weak_tip disabled"},
            )
            await db.commit()
            return ok(
                {
                    "delivered": False,
                    "degraded": False,
                    "message": "弱提示已关闭",
                    "schedule_id": item.id,
                }
            )
        await sse_hub.publish(
            int(channel_id),
            "weak_tip",
            {
                "schedule_id": item.id,
                "customer_id": item.customer_id,
                "text": tip_text,
                "priority": item.priority,
            },
        )
        await write_event(
            db,
            user_id=user["id"],
            action="schedule_remind_weak",
            customer_id=item.customer_id,
            ref_type="schedule_item",
            ref_id=item.id,
            meta={"delivered": True, "text": tip_text},
        )
        await db.commit()
        return ok(
            {
                "delivered": True,
                "degraded": False,
                "message": "弱提示已推送",
                "schedule_id": item.id,
            }
        )

    # strong: WeCom app message — degrade without crashing
    settings = get_settings()
    strong_enabled = pref.get("strong_notify", True)
    has_wecom = bool(
        not settings.mock_wecom
        and settings.wecom_corp_id
        and settings.wecom_secret
    )
    if not strong_enabled or not has_wecom:
        msg = (
            "强提醒已关闭"
            if strong_enabled is False
            else "无企微应用消息权限，已降级"
        )
        await write_event(
            db,
            user_id=user["id"],
            action="schedule_remind_strong",
            customer_id=item.customer_id,
            ref_type="schedule_item",
            ref_id=item.id,
            meta={"delivered": False, "degraded": True, "message": msg},
        )
        await db.commit()
        return ok(
            {
                "delivered": False,
                "degraded": True,
                "message": msg,
                "schedule_id": item.id,
            }
        )

    # Credentials present — still stub (no real send)
    await write_event(
        db,
        user_id=user["id"],
        action="schedule_remind_strong",
        customer_id=item.customer_id,
        ref_type="schedule_item",
        ref_id=item.id,
        meta={"delivered": False, "degraded": True, "message": "企微强提醒未接入"},
    )
    await db.commit()
    return ok(
        {
            "delivered": False,
            "degraded": True,
            "message": "企微强提醒未接入",
            "schedule_id": item.id,
        }
    )
