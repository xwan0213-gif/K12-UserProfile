from fastapi import APIRouter

from app.core.errors import ok

router = APIRouter(prefix="/sidebar/reply", tags=["reply-p2"])


@router.get("/_placeholder")
async def reply_placeholder():
    return ok({"phase": "P2", "message": "reply feature scaffold"})
