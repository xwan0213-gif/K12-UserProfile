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
    cid = customer_id or user.get("customer_id") or 0
    return StreamingResponse(
        event_stream(int(cid)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
