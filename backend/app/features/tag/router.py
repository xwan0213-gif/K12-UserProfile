from fastapi import APIRouter

from app.core.errors import ok

router = APIRouter(prefix="/sidebar/tags", tags=["tag"])


@router.get("/_placeholder")
async def tag_placeholder():
    return ok({"phase": "MVP", "message": "tag feature scaffold"})
