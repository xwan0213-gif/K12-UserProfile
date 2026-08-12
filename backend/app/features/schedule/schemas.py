"""Schedule API DTOs (request bodies)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

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
