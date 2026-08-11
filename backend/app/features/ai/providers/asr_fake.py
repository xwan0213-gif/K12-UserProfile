"""Fake ASR provider for local/demo — returns deterministic Chinese transcripts."""

from __future__ import annotations

from typing import Any


class FakeAsrProvider:
    """Deterministic Chinese transcript from audio_ref / content hint."""

    async def transcribe(
        self,
        audio_ref: str | None = None,
        bytes_meta: dict[str, Any] | None = None,
        *,
        content_hint: str | None = None,
    ) -> str:
        if content_hint and content_hint.strip():
            return content_hint.strip()

        meta = bytes_meta or {}
        hint = meta.get("content_hint") or meta.get("hint")
        if hint:
            return str(hint).strip()

        ref = (audio_ref or meta.get("audio_ref") or "").lower()
        if "complain" in ref or "投诉" in ref:
            return "老师，上次课孩子说听不太懂，能不能安排一次补课？"
        if "renew" in ref or "续费" in ref:
            return "课程快到期了，想了解一下续费优惠和班型。"
        if "absent" in ref or "请假" in ref:
            return "这周六孩子有事去不了，能不能改到下周补课？"
        if "trial" in ref or "试听" in ref:
            return "孩子周六下午有空，能否安排一次试听？"
        if audio_ref:
            return f"家长通过语音沟通：希望确认到课时间与补课安排。（ref={audio_ref[:48]}）"
        return "家长发来语音：想确认一下本周到课时间和补课安排。"


class StubAsrProvider:
    """Real vendor not wired — always fails with a clear AppError."""

    async def transcribe(
        self,
        audio_ref: str | None = None,
        bytes_meta: dict[str, Any] | None = None,
        *,
        content_hint: str | None = None,
    ) -> str:
        from app.core.errors import AppError, ErrorCode

        raise AppError(
            ErrorCode.AI_FAILED,
            "转写失败，不阻断后续文本建议",
            data={"reason": "ASR 厂商未接入", "audio_ref": audio_ref},
            http_status=500,
        )
