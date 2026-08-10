from fastapi import APIRouter

from app.core.errors import ok

router = APIRouter(prefix="/sidebar/schedules", tags=["schedule-p3"])


@router.get("/_placeholder")
async def schedule_placeholder():
    return ok({"phase": "P3", "message": "schedule feature scaffold"})
