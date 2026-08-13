"""侧边栏 ASR 转写 API：写入 chat_message.asr_text；失败不阻断后续文本建议。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.event_log import write_event
from app.core.models import ChatMessage
from app.core.scope import assert_customer_in_scope
from app.core.timeutil import utcnow_naive
from app.features.ai.gateway import get_asr

router = APIRouter(prefix="/sidebar/asr", tags=["asr"])


class TranscribeBody(BaseModel):
    """语音转写请求体；create_message=True 时同步落一条语音聊天消息。"""

    customer_id: int
    audio_ref: str | None = None
    content_hint: str | None = None
    msg_time: datetime | None = None
    create_message: bool = True


@router.post("/transcribe")
async def transcribe_audio(
    body: TranscribeBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """转写音频并可选写入聊天消息；转写失败以 AppError 返回，不阻塞话术建议流程。"""
    await assert_customer_in_scope(db, user, body.customer_id)
    settings = get_settings()

    try:
        asr = get_asr()
        transcript = await asr.transcribe(
            body.audio_ref,
            bytes_meta={"content_hint": body.content_hint} if body.content_hint else None,
            content_hint=body.content_hint,
        )
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001
        # 统一包装为业务错误，前端可继续走文本建议
        raise AppError(
            ErrorCode.AI_FAILED,
            "转写失败，不阻断后续文本建议",
            data={"detail": str(exc)},
            http_status=500,
        ) from exc

    if not transcript or not str(transcript).strip():
        raise AppError(
            ErrorCode.AI_FAILED,
            "转写失败，不阻断后续文本建议",
            http_status=500,
        )

    transcript = str(transcript).strip()
    message: ChatMessage | None = None
    if body.create_message:
        message = ChatMessage(
            customer_id=body.customer_id,
            direction="in",
            msg_type="voice",
            content=body.audio_ref or "[语音]",
            asr_text=transcript,
            msg_time=body.msg_time or utcnow_naive(),
            is_mock=bool(settings.mock_llm or settings.mock_wecom),
            raw={"audio_ref": body.audio_ref, "source": "asr_transcribe"},
        )
        db.add(message)
        await db.flush()

    await write_event(
        db,
        user_id=user["id"],
        action="asr_transcribe",
        customer_id=body.customer_id,
        ref_type="chat_message" if message else None,
        ref_id=message.id if message else None,
        meta={"audio_ref": body.audio_ref, "asr_len": len(transcript)},
    )
    await db.commit()
    if message:
        await db.refresh(message)

    return ok(
        {
            "asr_text": transcript,
            "message_id": message.id if message else None,
            "customer_id": body.customer_id,
        }
    )
