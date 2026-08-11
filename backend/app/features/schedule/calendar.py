"""WeCom calendar sync stub — always degrades when MOCK or no credentials."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.models import ScheduleItem


async def sync_to_wecom_calendar(item: ScheduleItem) -> tuple[bool, str | None]:
    """
    Attempt WeCom calendar sync.

    Always fails with reason 「企微日历未接入」 when MOCK or no credentials —
    caller should set sync_state=failed but KEEP the schedule_item.
    """
    settings = get_settings()
    if settings.mock_wecom or not (settings.wecom_corp_id and settings.wecom_secret):
        return False, "企微日历未接入"

    # Real vendor path not implemented — degrade clearly.
    _ = item
    return False, "企微日历未接入"
