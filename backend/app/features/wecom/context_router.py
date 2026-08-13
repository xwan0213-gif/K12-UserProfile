"""侧栏上下文：当前客户摘要与标签，供头区/能力区初始化。"""

from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.models import AppUser, Customer, CustomerTag, TagDef
from app.core.scope import assert_customer_in_scope

router = APIRouter(prefix="/sidebar", tags=["sidebar"])


@router.get("/context")
async def sidebar_context(
    user: CurrentUser,
    db: DbSession,
    customer_id: int | None = Query(default=None),
) -> dict[str, Any]:
    """按客户 ID（或 JWT 内 customer_id）返回客户基础信息与生效标签。"""
    cid = customer_id or user.get("customer_id")
    if cid is None:
        raise AppError(ErrorCode.PARAM, "缺少 customer_id", http_status=400)
    customer = await assert_customer_in_scope(db, user, int(cid))

    owner_name = None
    if customer.owner_user_id:
        owner = await db.get(AppUser, customer.owner_user_id)
        owner_name = owner.name if owner else None

    tag_rows = (
        await db.execute(
            select(TagDef)
            .join(CustomerTag, CustomerTag.tag_id == TagDef.id)
            .where(CustomerTag.customer_id == customer.id, TagDef.deleted_at.is_(None))
        )
    ).scalars().all()

    return ok(
        {
            "customer": {
                "id": customer.id,
                "parent_name": customer.parent_name,
                "student_name": customer.student_name,
                "grade": customer.grade,
                "school": customer.school,
                "stage": customer.stage,
                "owner_name": owner_name,
            },
            "tags": [{"id": t.id, "name": t.name} for t in tag_rows],
            # 弱提示由 SSE 实时推送，上下文接口固定占位
            "weak_tip": None,
        }
    )
