"""业务操作审计日志写入。"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import EventLog


async def write_event(
    db: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    customer_id: int | None = None,
    ref_type: str | None = None,
    ref_id: int | None = None,
    meta: dict[str, Any] | None = None,
) -> EventLog:
    """
    追加一条 event_log；调用方负责 commit。

    action 为业务动作名（如 profile_confirm_all）；ref_* 指向关联实体。
    """
    row = EventLog(
        user_id=user_id,
        customer_id=customer_id,
        action=action,
        ref_type=ref_type,
        ref_id=ref_id,
        meta=meta or {},
    )
    db.add(row)
    await db.flush()
    return row
