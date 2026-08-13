"""侧栏 Server-Sent Events：推送弱提示、草稿与任务状态等。"""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.deps import CurrentUser
from app.core.sse import event_stream

router = APIRouter(tags=["sse"])


@router.get("/sidebar/sse")
async def sidebar_sse(
    user: CurrentUser,
    customer_id: int | None = Query(default=None),
):
    """建立 SSE 长连接；通道为 customer_id（缺省用 JWT，再退 0）。"""
    cid = customer_id or user.get("customer_id") or 0
    return StreamingResponse(
        event_stream(int(cid)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # 关闭反向代理缓冲，避免 SSE 被攒批
            "X-Accel-Buffering": "no",
        },
    )
