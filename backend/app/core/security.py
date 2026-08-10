from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    subject: dict[str, Any],
    expires_seconds: int | None = None,
) -> tuple[str, int]:
    settings = get_settings()
    expire = expires_seconds or settings.jwt_expire_seconds
    payload = {
        **subject,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expire),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expire


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise AppError(
            ErrorCode.UNAUTHORIZED, "未登录或 ticket 无效", http_status=401
        ) from exc
