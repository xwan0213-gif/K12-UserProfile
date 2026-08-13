"""企微日历同步占位：Mock 或缺凭证时一律降级失败。"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.models import ScheduleItem


async def sync_to_wecom_calendar(item: ScheduleItem) -> tuple[bool, str | None]:
    """
    尝试同步到企微日历。

    Mock 或缺 corp/secret 时返回失败原因「企微日历未接入」；
    真实厂商路径未实现时同样降级。调用方应设 sync_state=failed，但保留 schedule_item。
    """
    settings = get_settings()
    if settings.mock_wecom or not (settings.wecom_corp_id and settings.wecom_secret):
        return False, "企微日历未接入"

    # 真实厂商接入尚未实现，明确降级
    _ = item
    return False, "企微日历未接入"
