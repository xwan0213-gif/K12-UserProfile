"""日程序列化、时间解析与日历同步门面。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.models import ScheduleItem, Suggestion
from app.features.schedule.calendar import sync_to_wecom_calendar


def serialize_item(row: ScheduleItem) -> dict[str, Any]:
    """将 ScheduleItem 转为侧栏 API 响应字典。"""
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


def serialize_draft(row: Suggestion) -> dict[str, Any]:
    """将 type=schedule 的 Suggestion 草稿展平为前端字段。"""
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


def parse_iso_dt(value: Any) -> datetime | None:
    """解析 ISO 时间字符串；统一去掉 tzinfo，非法值返回 None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str) and value.strip():
        try:
            # 兼容末尾 Z
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError:
            return None
    return None


async def apply_calendar_sync(item: ScheduleItem, sync_calendar: bool) -> None:
    """按开关调用企微日历同步，并回写 sync_state / external_cal_id。"""
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
