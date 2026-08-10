"""Profile feature shell — full pipeline in Stage 3."""

from typing import Any

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser
from app.core.errors import ok
from app.features.ai.gateway import get_gateway

router = APIRouter(prefix="/sidebar/profile", tags=["profile"])


@router.get("")
async def get_profile(
    user: CurrentUser,
    customer_id: int | None = Query(default=None),
) -> dict[str, Any]:
    cid = customer_id or user.get("customer_id")
    return ok(
        {
            "confirmed": None,
            "draft": None,
            "generating": False,
            "customer_id": cid,
            "note": "scaffold shell — Stage 3 will implement",
        }
    )


@router.post("/generate")
async def generate_profile_shell(
    user: CurrentUser,
    customer_id: int | None = Query(default=None),
) -> dict[str, Any]:
    """Scaffold: call FakeLLM / Gateway and return fixed JSON (no DB draft yet)."""
    gateway = get_gateway()
    result = await gateway.generate("profile", {"customer_id": customer_id})
    return ok(
        {
            "job_id": None,
            "status": "scaffold",
            "preview": result,
            "user_id": user["id"],
        }
    )
