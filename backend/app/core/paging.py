from typing import Any

from app.core.errors import AppError, ErrorCode


def require_roles(user: dict[str, Any], *roles: str) -> None:
    if user.get("role") not in roles:
        raise AppError(ErrorCode.FORBIDDEN, "无业务权限", http_status=403)


def page_meta(page: int, page_size: int, total: int) -> dict[str, int]:
    return {"page": page, "page_size": page_size, "total": total}


def clamp_page(page: int | None, page_size: int | None) -> tuple[int, int]:
    p = max(page or 1, 1)
    ps = min(max(page_size or 20, 1), 100)
    return p, ps
