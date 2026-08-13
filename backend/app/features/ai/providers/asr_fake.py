"""本地/演示用 ASR：Fake 返回确定性中文转写；Stub 表示厂商未接入并明确失败。"""

from __future__ import annotations

from typing import Any


class FakeAsrProvider:
    """确定性中文转写：优先 content_hint，其次按 audio_ref 关键字映射话术。"""

    async def transcribe(
        self,
        audio_ref: str | None = None,
        bytes_meta: dict[str, Any] | None = None,
        *,
        content_hint: str | None = None,
    ) -> str:
        """根据提示或引用关键字生成固定转写文本，不调用真实 ASR。

        参数:
            audio_ref: 音频引用；关键字如 trial/complain 会映射不同话术
            bytes_meta: 可含 content_hint / hint / audio_ref
            content_hint: 非空时直接作为转写结果
        返回:
            中文转写字符串
        """
        if content_hint and content_hint.strip():
            return content_hint.strip()

        meta = bytes_meta or {}
        hint = meta.get("content_hint") or meta.get("hint")
        if hint:
            return str(hint).strip()

        # 按 ref 关键字走场景化固定话术，便于联调各业务路径
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
    """真实 ASR 厂商未接入时的占位实现：始终抛 AppError，不返回假文本。"""

    async def transcribe(
        self,
        audio_ref: str | None = None,
        bytes_meta: dict[str, Any] | None = None,
        *,
        content_hint: str | None = None,
    ) -> str:
        """始终失败，提示「ASR 厂商未接入」；上层可捕获后降级到纯文本建议。"""
        from app.core.errors import AppError, ErrorCode

        raise AppError(
            ErrorCode.AI_FAILED,
            "转写失败，不阻断后续文本建议",
            data={"reason": "ASR 厂商未接入", "audio_ref": audio_ref},
            http_status=500,
        )
