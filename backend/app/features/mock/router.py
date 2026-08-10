from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import DbSession
from app.core.errors import ok
from app.core.models import (
    AdminAccount,
    AppUser,
    ChatMessage,
    CsSummary,
    Customer,
    OrderRecord,
    Org,
    TagDef,
)
from app.core.security import hash_password

router = APIRouter(prefix="/mock", tags=["mock"])


def _utcnow_naive() -> datetime:
    """DB columns are TIMESTAMP WITHOUT TIME ZONE; store UTC as naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MockMessageBody(BaseModel):
    customer_id: int
    direction: str = "in"
    msg_type: str = "text"
    content: str
    msg_time: datetime | None = None


class MockOrderBody(BaseModel):
    customer_id: int
    title: str
    amount: float = 0
    status: str = "paid"
    external_order_no: str | None = None


@router.post("/seed/demo")
async def seed_demo(db: DbSession) -> dict[str, Any]:
    """Seed org / 三角色 / 演示客户（王女士）/ tags — scaffold shell with real rows."""
    settings = get_settings()

    existing = await db.execute(select(Org).where(Org.code == "HQ"))
    if existing.scalar_one_or_none():
        return ok({"seeded": False, "message": "demo data already exists"})

    hq = Org(name="总部", code="HQ")
    db.add(hq)
    await db.flush()
    region = Org(name="华东区", parent_id=hq.id, code="HD")
    db.add(region)
    await db.flush()

    admin_user = AppUser(name="张建国", role="admin", wecom_userid="admin_demo")
    regional = AppUser(
        name="王区域", role="regional", org_id=region.id, wecom_userid="regional_demo"
    )
    advisor = AppUser(
        name="李顾问", role="advisor", org_id=region.id, wecom_userid="advisor_demo"
    )
    db.add_all([admin_user, regional, advisor])
    await db.flush()

    db.add(
        AdminAccount(
            user_id=admin_user.id,
            login_name=settings.seed_admin_login,
            password_hash=hash_password(settings.seed_admin_password),
        )
    )

    tags = [
        TagDef(name="高意向", sort_order=1, sop_text="48h 内邀约试听"),
        TagDef(name="数学薄弱", sort_order=2, sop_text="推荐数学诊断"),
        TagDef(name="初中", sort_order=3),
        TagDef(name="刚加微信", sort_order=4),
        TagDef(name="近期决策", sort_order=5),
    ]
    db.add_all(tags)
    await db.flush()

    customer = Customer(
        external_id="demo_wang",
        parent_name="王女士",
        student_name="王小明",
        grade="初二",
        school="城南实验中学",
        stage="junior",
        owner_user_id=advisor.id,
        org_id=region.id,
        last_contact_at=_utcnow_naive(),
    )
    db.add(customer)
    await db.flush()

    now = _utcnow_naive()
    db.add_all(
        [
            ChatMessage(
                customer_id=customer.id,
                direction="in",
                msg_type="text",
                content="想了解一下初二数学班",
                msg_time=now,
                is_mock=True,
            ),
            ChatMessage(
                customer_id=customer.id,
                direction="out",
                msg_type="text",
                content="王女士您好，方便说下孩子目前成绩吗？",
                msg_time=now,
                is_mock=True,
            ),
            OrderRecord(
                customer_id=customer.id,
                external_order_no="#1024",
                title="初二数学体验课",
                amount=99,
                status="paid",
                paid_at=now,
            ),
            CsSummary(
                customer_id=customer.id,
                summary_text="家长关注师资与试听安排，价格敏感中等。",
                updated_by=admin_user.id,
            ),
        ]
    )
    await db.commit()
    return ok(
        {
            "seeded": True,
            "admin_login": settings.seed_admin_login,
            "admin_password": settings.seed_admin_password,
            "customer_id": customer.id,
            "advisor_id": advisor.id,
            "hint": "Mock token: Bearer mock-<advisor_id>",
        }
    )


@router.post("/messages")
async def mock_messages(body: MockMessageBody, db: DbSession) -> dict[str, Any]:
    row = ChatMessage(
        customer_id=body.customer_id,
        direction=body.direction,
        msg_type=body.msg_type,
        content=body.content,
        msg_time=body.msg_time or _utcnow_naive(),
        is_mock=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id})


@router.post("/orders")
async def mock_orders(body: MockOrderBody, db: DbSession) -> dict[str, Any]:
    row = OrderRecord(
        customer_id=body.customer_id,
        title=body.title,
        amount=body.amount,
        status=body.status,
        external_order_no=body.external_order_no,
        paid_at=_utcnow_naive() if body.status == "paid" else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id})
