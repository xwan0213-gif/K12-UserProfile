from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import AppError, ErrorCode
from app.core.models import AppUser
from app.core.security import decode_access_token

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(ErrorCode.UNAUTHORIZED, "未登录或 ticket 无效", http_status=401)

    token = authorization.split(" ", 1)[1].strip()
    settings = get_settings()

    # Mock debug token: Bearer mock-<user_id>
    if settings.mock_wecom and token.startswith("mock-"):
        try:
            user_id = int(token.removeprefix("mock-"))
        except ValueError as exc:
            raise AppError(
                ErrorCode.UNAUTHORIZED, "未登录或 ticket 无效", http_status=401
            ) from exc
        result = await db.execute(
            select(AppUser).where(AppUser.id == user_id, AppUser.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise AppError(ErrorCode.UNAUTHORIZED, "用户不存在", http_status=401)
        return {
            "id": user.id,
            "name": user.name,
            "role": user.role,
            "org_id": user.org_id,
            "auth_type": "mock",
        }

    payload = decode_access_token(token)
    user_id = payload.get("sub") or payload.get("user_id")
    if user_id is None:
        raise AppError(ErrorCode.UNAUTHORIZED, "未登录或 ticket 无效", http_status=401)

    result = await db.execute(
        select(AppUser).where(
            AppUser.id == int(user_id), AppUser.deleted_at.is_(None)
        )
    )
    user = result.scalar_one_or_none()
    if user is None or user.status != 1:
        raise AppError(ErrorCode.UNAUTHORIZED, "用户不可用", http_status=401)

    return {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "org_id": user.org_id,
        "auth_type": payload.get("auth_type", "jwt"),
        "customer_id": payload.get("customer_id"),
    }


CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
