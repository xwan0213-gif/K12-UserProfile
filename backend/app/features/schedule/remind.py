"""日程提醒策略：弱提示走 SSE，强提醒走企微（可降级）。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.event_log import write_event
from app.core.models import AppUser, ScheduleItem
from app.core.sse import sse_hub


async def remind_schedule(
    db: AsyncSession,
    *,
    item: ScheduleItem,
    user: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """按 mode 分发弱/强提醒，返回投递与降级结果。"""
    owner = await db.get(AppUser, user["id"])
    pref = dict(owner.remind_pref or {}) if owner else {}
    # 无客户时退回到用户自身通道，保证 SSE 仍可投递
    channel_id = item.customer_id or user["id"]
    tip_text = f"{item.title}" + (
        f" · {item.start_at.isoformat()}" if item.start_at else ""
    )

    if mode == "weak":
        return await _weak_remind(
            db, item=item, user=user, pref=pref, channel_id=int(channel_id), tip_text=tip_text
        )
    return await _strong_remind(db, item=item, user=user, pref=pref)


async def _weak_remind(
    db: AsyncSession,
    *,
    item: ScheduleItem,
    user: dict[str, Any],
    pref: dict[str, Any],
    channel_id: int,
    tip_text: str,
) -> dict[str, Any]:
    """弱提示：尊重 weak_tip 偏好，成功则向 SSE 通道推送。"""
    if pref.get("weak_tip", True) is False:
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
        return {
            "delivered": False,
            "degraded": False,
            "message": "弱提示已关闭",
            "schedule_id": item.id,
        }

    await sse_hub.publish(
        channel_id,
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
    return {
        "delivered": True,
        "degraded": False,
        "message": "弱提示已推送",
        "schedule_id": item.id,
    }


async def _strong_remind(
    db: AsyncSession,
    *,
    item: ScheduleItem,
    user: dict[str, Any],
    pref: dict[str, Any],
) -> dict[str, Any]:
    """强提醒：偏好关闭或缺企微凭证则降级；当前厂商消息未接入。"""
    settings = get_settings()
    strong_enabled = pref.get("strong_notify", True)
    has_wecom = bool(
        not settings.mock_wecom and settings.wecom_corp_id and settings.wecom_secret
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
        return {
            "delivered": False,
            "degraded": True,
            "message": msg,
            "schedule_id": item.id,
        }

    # 凭证齐全但强提醒通道尚未实现，仍记为降级
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
    return {
        "delivered": False,
        "degraded": True,
        "message": "企微强提醒未接入",
        "schedule_id": item.id,
    }
