"""侧栏聊天消息列表：供聊天框只读拉取（Mock/真实共用读路径）。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.models import ChatMessage
from app.core.scope import assert_customer_in_scope

router = APIRouter(prefix="/sidebar", tags=["sidebar-messages"])


def _serialize_message(row: ChatMessage) -> dict[str, Any]:
    """将 ChatMessage 转为侧栏消息项。"""
    return {
        "id": row.id,
        "customer_id": row.customer_id,
        "direction": row.direction,
        "msg_type": row.msg_type,
        "content": row.content,
        "asr_text": row.asr_text,
        "msg_time": row.msg_time.isoformat() + "Z" if row.msg_time else None,
        "is_mock": bool(row.is_mock),
    }


@router.get("/messages")
async def list_messages(
    user: CurrentUser,
    db: DbSession,
    customer_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """按客户拉取聊天消息（时间正序，最多 limit 条）。"""
    cid = customer_id or user.get("customer_id")
    if cid is None:
        raise AppError(ErrorCode.PARAM, "缺少 customer_id", http_status=400)
    await assert_customer_in_scope(db, user, int(cid))

    rows = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.customer_id == int(cid))
            .order_by(ChatMessage.msg_time.asc(), ChatMessage.id.asc())
            .limit(limit)
        )
    ).scalars().all()

    return ok(
        {
            "customer_id": int(cid),
            "items": [_serialize_message(r) for r in rows],
        }
    )
