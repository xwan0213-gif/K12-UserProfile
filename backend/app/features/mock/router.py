"""Mock / 演示数据路由：种子组织用户、模拟客户/消息/订单，仅用于联调与演示。"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.models import (
    AdminAccount,
    AppUser,
    ChatMessage,
    CsSummary,
    Customer,
    CustomerTag,
    OrderRecord,
    Org,
    ScriptTemplate,
    TagDef,
)
from app.core.security import hash_password

router = APIRouter(prefix="/mock", tags=["mock"])


def _utcnow_naive() -> datetime:
    """返回当前 UTC 时间的 naive datetime（库表为 TIMESTAMP WITHOUT TIME ZONE）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive_msg_time(msg_time: datetime | None) -> datetime:
    """将消息时间规范为 naive UTC；缺省则取当前时间。"""
    if msg_time is None:
        return _utcnow_naive()
    # 去掉时区信息，与 DB 列类型对齐
    if msg_time.tzinfo is not None:
        return msg_time.replace(tzinfo=None)
    return msg_time


async def _default_advisor(db: DbSession) -> AppUser:
    """取一名可用顾问；若无则提示先执行 seed/demo。"""
    result = await db.execute(
        select(AppUser).where(
            AppUser.role == "advisor",
            AppUser.deleted_at.is_(None),
            AppUser.status == 1,
        )
    )
    advisor = result.scalars().first()
    if advisor is None:
        raise AppError(
            ErrorCode.NOT_FOUND,
            "无可用顾问，请先执行 POST /mock/seed/demo",
            http_status=404,
        )
    return advisor


class MockMessageBody(BaseModel):
    """模拟聊天消息请求体。"""

    customer_id: int
    direction: str = "in"
    msg_type: str = "text"
    content: str
    asr_text: str | None = None
    msg_time: datetime | None = None


class MockOrderBody(BaseModel):
    """模拟订单请求体。"""

    customer_id: int
    title: str
    amount: float = 0
    status: str = "paid"
    external_order_no: str | None = None


class MockCustomerBody(BaseModel):
    """创建模拟客户请求体。"""

    parent_name: str
    student_name: str | None = None
    grade: str | None = None
    school: str | None = None
    stage: str | None = None
    external_id: str | None = None
    owner_user_id: int | None = None
    org_id: int | None = None
    remark: str | None = None


class ScenarioMessage(BaseModel):
    """场景种子中的单条聊天消息。"""

    direction: str = "in"
    msg_type: str = "text"
    content: str
    asr_text: str | None = None


class MockScenarioBody(BaseModel):
    """按场景创建（或按 external_id 复用）客户并灌入聊天记录。"""

    parent_name: str
    student_name: str | None = None
    grade: str | None = None
    school: str | None = None
    stage: str | None = None
    external_id: str | None = None
    owner_user_id: int | None = None
    org_id: int | None = None
    remark: str | None = None
    messages: list[ScenarioMessage] = Field(default_factory=list)
    append_messages: bool = True
    cs_summary: str | None = None


# ---------- 种子演示数据 ----------


@router.post("/seed/demo")
async def seed_demo(db: DbSession) -> dict[str, Any]:
    """种子：组织 / 三角色账号 / 演示客户（王女士）/ 标签与话术模板。"""
    settings = get_settings()

    # 已存在 HQ 组织则视为已播种，避免重复插入
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

    db.add_all(
        [
            AdminAccount(
                user_id=admin_user.id,
                login_name=settings.seed_admin_login,
                password_hash=hash_password(settings.seed_admin_password),
            ),
            AdminAccount(
                user_id=regional.id,
                login_name="regional",
                password_hash=hash_password("regional123"),
            ),
            AdminAccount(
                user_id=advisor.id,
                login_name="advisor",
                password_hash=hash_password("advisor123"),
            ),
        ]
    )

    tags = [
        TagDef(name="高意向", sort_order=1, sop_text="48h 内邀约试听"),
        TagDef(name="数学薄弱", sort_order=2, sop_text="推荐数学诊断"),
        TagDef(name="初中", sort_order=3, sop_text="按初中学段话术跟进"),
        TagDef(name="刚加微信", sort_order=4),
        TagDef(name="近期决策", sort_order=5, sop_text="24h 内确认试听时间"),
    ]
    db.add_all(tags)
    await db.flush()

    db.add_all(
        [
            ScriptTemplate(
                scene="sales",
                stage="junior",
                title="初中试听邀约",
                content="家长您好，结合孩子近期薄弱点，建议先安排一次诊断/试听再谈班型。",
                enabled=True,
            ),
            ScriptTemplate(
                scene="cs",
                stage=None,
                title="请假补课",
                content="已记录请假诉求，可协调同进度补课并确认下次到课时间。",
                enabled=True,
            ),
            ScriptTemplate(
                scene="cs",
                stage="junior",
                title="续费沟通",
                content="课程临近节点，可梳理剩余课时与续费档位，方便对照选择。",
                enabled=True,
            ),
        ]
    )

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

    # 绑定演示标签：高意向 / 数学薄弱 / 初中
    for tag in tags[:3]:
        db.add(
            CustomerTag(
                customer_id=customer.id,
                tag_id=tag.id,
                source="manual",
                created_by=advisor.id,
            )
        )

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
            ChatMessage(
                customer_id=customer.id,
                direction="in",
                msg_type="text",
                content="期中大概70分，想夯实基础，先试听看看老师",
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
            "accounts": {
                "admin": settings.seed_admin_login,
                "regional": "regional/regional123",
                "advisor": "advisor/advisor123",
            },
            "customer_id": customer.id,
            "advisor_id": advisor.id,
            "hint": "Mock token: Bearer mock-<advisor_id>",
        }
    )


# ---------- 模拟客户 ----------


@router.get("/customers")
async def list_mock_customers(
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """列出未删除的客户（按 id 倒序，带 limit）。"""
    rows = (
        await db.execute(
            select(Customer)
            .where(Customer.deleted_at.is_(None))
            .order_by(Customer.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    return ok(
        {
            "items": [
                {
                    "id": c.id,
                    "external_id": c.external_id,
                    "parent_name": c.parent_name,
                    "student_name": c.student_name,
                    "grade": c.grade,
                    "school": c.school,
                    "stage": c.stage,
                    "owner_user_id": c.owner_user_id,
                    "org_id": c.org_id,
                }
                for c in rows
            ]
        }
    )


@router.post("/customers")
async def create_mock_customer(
    body: MockCustomerBody, db: DbSession
) -> dict[str, Any]:
    """创建模拟客户；external_id 冲突时返回 409。"""
    if body.external_id:
        existing = (
            await db.execute(
                select(Customer).where(
                    Customer.external_id == body.external_id,
                    Customer.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise AppError(
                ErrorCode.CONFLICT,
                f"external_id 已存在: {body.external_id}",
                data={"customer_id": existing.id},
                http_status=409,
            )

    # 未指定归属顾问或组织时，回落到默认顾问
    advisor = None
    if body.owner_user_id is None or body.org_id is None:
        advisor = await _default_advisor(db)

    owner_id = body.owner_user_id or (advisor.id if advisor else None)
    org_id = body.org_id
    if org_id is None and advisor is not None:
        org_id = advisor.org_id

    customer = Customer(
        external_id=body.external_id,
        parent_name=body.parent_name,
        student_name=body.student_name,
        grade=body.grade,
        school=body.school,
        stage=body.stage,
        owner_user_id=owner_id,
        org_id=org_id,
        remark=body.remark,
        last_contact_at=_utcnow_naive(),
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return ok(
        {
            "id": customer.id,
            "external_id": customer.external_id,
            "parent_name": customer.parent_name,
            "student_name": customer.student_name,
            "owner_user_id": customer.owner_user_id,
            "org_id": customer.org_id,
        }
    )


@router.post("/seed/scenario")
async def seed_scenario(body: MockScenarioBody, db: DbSession) -> dict[str, Any]:
    """按 external_id 复用或新建客户，并灌入模拟聊天与客服摘要。"""
    customer: Customer | None = None
    created = False
    if body.external_id:
        customer = (
            await db.execute(
                select(Customer).where(
                    Customer.external_id == body.external_id,
                    Customer.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

    if customer is None:
        advisor = None
        if body.owner_user_id is None or body.org_id is None:
            advisor = await _default_advisor(db)
        owner_id = body.owner_user_id or (advisor.id if advisor else None)
        org_id = body.org_id if body.org_id is not None else (
            advisor.org_id if advisor else None
        )
        customer = Customer(
            external_id=body.external_id,
            parent_name=body.parent_name,
            student_name=body.student_name,
            grade=body.grade,
            school=body.school,
            stage=body.stage,
            owner_user_id=owner_id,
            org_id=org_id,
            remark=body.remark,
            last_contact_at=_utcnow_naive(),
        )
        db.add(customer)
        await db.flush()
        created = True
    else:
        # 已存在则刷新画像字段，便于反复演示同一场景
        customer.parent_name = body.parent_name
        if body.student_name is not None:
            customer.student_name = body.student_name
        if body.grade is not None:
            customer.grade = body.grade
        if body.school is not None:
            customer.school = body.school
        if body.stage is not None:
            customer.stage = body.stage
        if body.remark is not None:
            customer.remark = body.remark
        customer.last_contact_at = _utcnow_naive()

    message_ids: list[int] = []
    if body.messages:
        # append_messages=False 且非新建时，先清空该客户历史消息再写入
        if not body.append_messages and not created:
            old = (
                await db.execute(
                    select(ChatMessage).where(ChatMessage.customer_id == customer.id)
                )
            ).scalars().all()
            for row in old:
                await db.delete(row)

        for msg in body.messages:
            row = ChatMessage(
                customer_id=customer.id,
                direction=msg.direction,
                msg_type=msg.msg_type,
                content=msg.content,
                asr_text=msg.asr_text,
                msg_time=_utcnow_naive(),
                is_mock=True,
            )
            db.add(row)
            await db.flush()
            message_ids.append(row.id)

    if body.cs_summary:
        cs = (
            await db.execute(
                select(CsSummary).where(CsSummary.customer_id == customer.id)
            )
        ).scalar_one_or_none()
        if cs is None:
            db.add(
                CsSummary(
                    customer_id=customer.id,
                    summary_text=body.cs_summary,
                    updated_by=customer.owner_user_id,
                )
            )
        else:
            cs.summary_text = body.cs_summary

    await db.commit()
    await db.refresh(customer)
    return ok(
        {
            "created": created,
            "customer_id": customer.id,
            "external_id": customer.external_id,
            "parent_name": customer.parent_name,
            "student_name": customer.student_name,
            "message_ids": message_ids,
            "hint": "POST /sidebar/profile/generate with this customer_id",
        }
    )


# ---------- 模拟消息 / 订单 ----------


@router.post("/messages")
async def mock_messages(body: MockMessageBody, db: DbSession) -> dict[str, Any]:
    """写入一条模拟聊天消息，并更新客户最近联系时间。"""
    customer = await db.get(Customer, body.customer_id)
    if customer is None or customer.deleted_at is not None:
        raise AppError(ErrorCode.NOT_FOUND, "客户不存在", http_status=404)

    row = ChatMessage(
        customer_id=body.customer_id,
        direction=body.direction,
        msg_type=body.msg_type,
        content=body.content,
        asr_text=body.asr_text,
        msg_time=_naive_msg_time(body.msg_time),
        is_mock=True,
    )
    db.add(row)
    customer.last_contact_at = row.msg_time
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id, "customer_id": row.customer_id})


@router.post("/orders")
async def mock_orders(body: MockOrderBody, db: DbSession) -> dict[str, Any]:
    """写入一条模拟订单；status=paid 时自动填 paid_at。"""
    customer = await db.get(Customer, body.customer_id)
    if customer is None or customer.deleted_at is not None:
        raise AppError(ErrorCode.NOT_FOUND, "客户不存在", http_status=404)

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
