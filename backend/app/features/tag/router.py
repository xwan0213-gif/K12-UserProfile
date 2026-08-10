from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.models import CustomerTag, TagDef
from app.core.scope import assert_customer_in_scope

router = APIRouter(prefix="/sidebar/tags", tags=["tag"])


class AddTagBody(BaseModel):
    customer_id: int
    tag_id: int


@router.get("")
async def list_sidebar_tags(
    user: CurrentUser,
    db: DbSession,
    customer_id: int | None = Query(default=None),
) -> dict[str, Any]:
    cid = customer_id or user.get("customer_id")
    if cid is None:
        raise AppError(ErrorCode.PARAM, "缺少 customer_id", http_status=400)
    await assert_customer_in_scope(db, user, int(cid))

    rows = (
        await db.execute(
            select(CustomerTag, TagDef)
            .join(TagDef, TagDef.id == CustomerTag.tag_id)
            .where(CustomerTag.customer_id == int(cid), TagDef.deleted_at.is_(None))
        )
    ).all()

    active = [
        {
            "id": tag.id,
            "customer_tag_id": ct.id,
            "name": tag.name,
            "sop_text": tag.sop_text,
        }
        for ct, tag in rows
    ]
    return ok({"active": active, "recommendations": None})


@router.post("")
async def add_sidebar_tag(
    body: AddTagBody,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    await assert_customer_in_scope(db, user, body.customer_id)
    tag = await db.get(TagDef, body.tag_id)
    if tag is None or tag.deleted_at is not None or not tag.enabled:
        raise AppError(ErrorCode.NOT_FOUND, "标签不存在或未启用", http_status=404)

    existing = (
        await db.execute(
            select(CustomerTag).where(
                CustomerTag.customer_id == body.customer_id,
                CustomerTag.tag_id == body.tag_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return ok({"id": existing.id, "created": False})

    row = CustomerTag(
        customer_id=body.customer_id,
        tag_id=body.tag_id,
        source="manual",
        created_by=user["id"],
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id, "created": True})


@router.delete("/{customer_tag_id}")
async def remove_sidebar_tag(
    customer_tag_id: int,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    row = await db.get(CustomerTag, customer_tag_id)
    if row is None:
        raise AppError(ErrorCode.NOT_FOUND, "客户标签不存在", http_status=404)
    await assert_customer_in_scope(db, user, row.customer_id)
    await db.delete(row)
    await db.commit()
    return ok({"deleted": True})
