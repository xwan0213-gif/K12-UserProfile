from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.core.errors import ok

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/_health")
async def admin_shell(user: CurrentUser):
    return ok({"phase": "MVP", "message": "admin feature scaffold", "user": user})
