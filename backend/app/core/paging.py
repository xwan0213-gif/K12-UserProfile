"""分页参数与角色校验小工具。"""

from typing import Any

from app.core.errors import AppError, ErrorCode


def require_roles(user: dict[str, Any], *roles: str) -> None:
    """当前用户角色不在允许列表时抛 403。"""
    if user.get("role") not in roles:
        raise AppError(ErrorCode.FORBIDDEN, "无业务权限", http_status=403)


def page_meta(page: int, page_size: int, total: int) -> dict[str, int]:
    """列表接口分页元信息。"""
    return {"page": page, "page_size": page_size, "total": total}


def clamp_page(page: int | None, page_size: int | None) -> tuple[int, int]:
    """规范化页码（≥1）与页大小（1~100，默认 20）。"""
    p = max(page or 1, 1)
    ps = min(max(page_size or 20, 1), 100)
    return p, ps
