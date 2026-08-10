"""apply_scope: filter queries by role data range (FR-ADMIN-02)."""

from collections.abc import Sequence

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.core.models import Customer, Org


async def _org_subtree_ids(db: AsyncSession, root_org_id: int) -> list[int]:
    """BFS collect org id and descendants (small tree, MVP)."""
    result = await db.execute(select(Org.id, Org.parent_id).where(Org.deleted_at.is_(None)))
    rows = result.all()
    children: dict[int | None, list[int]] = {}
    for oid, parent_id in rows:
        children.setdefault(parent_id, []).append(oid)

    collected: list[int] = []
    stack = [root_org_id]
    while stack:
        cur = stack.pop()
        collected.append(cur)
        stack.extend(children.get(cur, []))
    return collected


async def apply_scope(
    query: Select,
    user: dict,
    db: AsyncSession,
    *,
    customer_alias: type = Customer,
) -> Select:
    role = user.get("role")
    if role == "admin":
        return query
    if role == "regional":
        org_id = user.get("org_id")
        if org_id is None:
            raise AppError(ErrorCode.FORBIDDEN, "区域主管未绑定组织", http_status=403)
        org_ids = await _org_subtree_ids(db, int(org_id))
        return query.where(customer_alias.org_id.in_(org_ids))
    if role == "advisor":
        return query.where(customer_alias.owner_user_id == user["id"])
    raise AppError(ErrorCode.FORBIDDEN, "未知角色", http_status=403)


async def assert_customer_in_scope(
    db: AsyncSession,
    user: dict,
    customer_id: int,
) -> Customer:
    q = select(Customer).where(
        Customer.id == customer_id,
        Customer.deleted_at.is_(None),
    )
    q = await apply_scope(q, user, db)
    result = await db.execute(q)
    customer = result.scalar_one_or_none()
    if customer is None:
        raise AppError(ErrorCode.FORBIDDEN, "无业务权限（数据范围外）", http_status=403)
    return customer


def org_ids_filter(org_ids: Sequence[int]):
    return or_(Customer.org_id.in_(list(org_ids)))
