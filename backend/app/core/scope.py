"""数据范围（FR-ADMIN-02）：按角色过滤客户查询。"""

from collections.abc import Sequence

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.core.models import Customer, Org


async def _org_subtree_ids(db: AsyncSession, root_org_id: int) -> list[int]:
    """BFS 收集某组织及其全部子组织 id（MVP 组织树较小，全量加载后内存遍历）。"""
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
    """
    按角色给客户相关查询加范围条件。

    - admin：不过滤
    - regional：本组织及子组织下的客户
    - advisor：仅本人负责的客户
    """
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
    """校验客户存在且在当前用户数据范围内；否则 403。"""
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
    """客户 org_id IN (...) 条件辅助。"""
    return or_(Customer.org_id.in_(list(org_ids)))
