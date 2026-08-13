"""日程侧栏 API 的请求体 DTO 定义。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["high", "medium", "low"]
ScheduleStatus = Literal["draft", "confirmed", "done", "cancelled"]


class SuggestBody(BaseModel):
    """触发生成日程建议。"""

    customer_id: int
    force: bool = False


class ScheduleEdits(BaseModel):
    """确认/采纳前对建议内容的可选覆盖字段。"""

    title: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: Priority | None = None
    remark: str | None = None


class ConfirmBody(BaseModel):
    """确认建议或草稿日程；可选同步企微日历。"""

    suggestion_id: int | None = None
    schedule_id: int | None = None
    sync_calendar: bool = False
    edits: ScheduleEdits | None = None


class CreateBody(BaseModel):
    """手工新建已确认日程。"""

    customer_id: int
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: Priority = "medium"
    remark: str | None = None
    sync_calendar: bool = False


class PatchBody(BaseModel):
    """部分更新日程字段（仅提交的字段生效）。"""

    title: str | None = Field(default=None, max_length=200)
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority: Priority | None = None
    status: ScheduleStatus | None = None
    remark: str | None = None


class PrefBody(BaseModel):
    """提醒偏好补丁；允许额外键以便前端扩展。"""

    weak_tip: bool | None = None
    strong_notify: bool | None = None
    quiet_hours: list[str] | None = None

    model_config = {"extra": "allow"}


class DismissBody(BaseModel):
    """忽略 AI 日程草稿（不生成站内待办）。"""

    suggestion_id: int


class RemindBody(BaseModel):
    """触发弱提示（SSE）或强提醒（企微，可降级）。"""

    mode: Literal["weak", "strong"]
