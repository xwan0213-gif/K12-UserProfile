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
