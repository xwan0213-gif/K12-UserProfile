from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.models import AppUser, Customer
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class WecomExchangeBody(BaseModel):
    code: str = Field(..., description="企微 OAuth code 或 mock_code")
    external_userid: str | None = Field(
        default=None, description="外部联系人 ID，Mock 可传 demo_wang"
    )


class AdminLoginBody(BaseModel):
    login_name: str
    password: str


@router.post("/wecom/exchange")
async def wecom_exchange(body: WecomExchangeBody, db: DbSession) -> dict[str, Any]:
    settings = get_settings()
    if not settings.mock_wecom and body.code != "mock_code":
        # Real WeCom OAuth not wired in scaffold; keep adapter shell.
        raise AppError(
            ErrorCode.INTERNAL,
            "真实企微换票尚未接入，请开启 MOCK_WECOM",
            http_status=501,
        )

    # Prefer advisor with wecom_userid match, else first advisor
    result = await db.execute(
        select(AppUser).where(
            AppUser.role == "advisor",
            AppUser.deleted_at.is_(None),
            AppUser.status == 1,
        )
    )
    user = result.scalars().first()
    if user is None:
        raise AppError(
            ErrorCode.NOT_FOUND,
            "无可用顾问，请先执行 POST /mock/seed/demo",
            http_status=404,
        )

    customer_id = None
    if body.external_userid:
        c_result = await db.execute(
            select(Customer).where(
                Customer.external_id == body.external_userid,
                Customer.deleted_at.is_(None),
            )
        )
        customer = c_result.scalar_one_or_none()
        if customer is None and body.external_userid == "demo_wang":
            c_result = await db.execute(
                select(Customer).where(
                    Customer.parent_name == "王女士",
                    Customer.deleted_at.is_(None),
                )
            )
            customer = c_result.scalars().first()
        if customer:
            customer_id = customer.id

    token, expires = create_access_token(
        {
            "sub": str(user.id),
            "user_id": user.id,
            "role": user.role,
            "org_id": user.org_id,
            "auth_type": "wecom",
            "customer_id": customer_id,
        },
        expires_seconds=settings.wecom_token_expire_seconds,
    )
    return ok(
        {
            "access_token": token,
            "expires_in": expires,
            "user": {
                "id": user.id,
                "name": user.name,
                "role": user.role,
                "org_id": user.org_id,
            },
            "customer_id": customer_id,
        }
    )


@router.post("/admin/login")
async def admin_login(body: AdminLoginBody, db: DbSession) -> dict[str, Any]:
    from app.core.models import AdminAccount
    from app.core.security import verify_password

    result = await db.execute(
        select(AdminAccount).where(AdminAccount.login_name == body.login_name)
    )
    account = result.scalar_one_or_none()
    if account is None or not verify_password(body.password, account.password_hash):
        raise AppError(ErrorCode.UNAUTHORIZED, "用户名或密码错误", http_status=401)

    user_result = await db.execute(
        select(AppUser).where(AppUser.id == account.user_id, AppUser.deleted_at.is_(None))
    )
    user = user_result.scalar_one_or_none()
    if user is None or user.status != 1:
        raise AppError(ErrorCode.UNAUTHORIZED, "用户不可用", http_status=401)

    from datetime import datetime, timezone

    account.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    settings = get_settings()
    token, expires = create_access_token(
        {
            "sub": str(user.id),
            "user_id": user.id,
            "role": user.role,
            "org_id": user.org_id,
            "auth_type": "admin",
        },
        expires_seconds=settings.jwt_expire_seconds,
    )
    return ok(
        {
            "access_token": token,
            "expires_in": expires,
            "user": {"id": user.id, "name": user.name, "role": user.role},
        }
    )


@router.get("/me")
async def auth_me(user: CurrentUser) -> dict[str, Any]:
    return ok(user)
