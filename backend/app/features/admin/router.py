from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.core.deps import CurrentUser, DbSession
from app.core.errors import AppError, ErrorCode, ok
from app.core.models import (
    AdminAccount,
    AppUser,
    ChatMessage,
    CsSummary,
    Customer,
    CustomerProfile,
    CustomerTag,
    EventLog,
    OrderRecord,
    Org,
    ProfileDraft,
    ScriptTemplate,
    Suggestion,
    TagDef,
)
from app.core.paging import clamp_page, page_meta, require_roles
from app.core.scope import apply_scope, assert_customer_in_scope
from app.core.security import hash_password
from app.core.timeutil import utcnow_naive
from app.features.profile.router import _serialize_confirmed, _serialize_draft

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- Orgs ----------


class OrgCreate(BaseModel):
    name: str
    parent_id: int | None = None
    code: str | None = None


class OrgPatch(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    code: str | None = None


@router.get("/orgs")
async def list_orgs(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    require_roles(user, "admin", "regional")
    rows = (
        await db.execute(select(Org).where(Org.deleted_at.is_(None)).order_by(Org.id))
    ).scalars().all()
    items = [
        {
            "id": o.id,
            "name": o.name,
            "parent_id": o.parent_id,
            "code": o.code,
        }
        for o in rows
    ]
    return ok({"items": items})


@router.post("/orgs")
async def create_org(body: OrgCreate, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    require_roles(user, "admin")
    org = Org(name=body.name, parent_id=body.parent_id, code=body.code)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return ok({"id": org.id})


@router.patch("/orgs/{org_id}")
async def patch_org(
    org_id: int, body: OrgPatch, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    require_roles(user, "admin")
    org = await db.get(Org, org_id)
    if org is None or org.deleted_at is not None:
        raise AppError(ErrorCode.NOT_FOUND, "组织不存在", http_status=404)
    if body.name is not None:
        org.name = body.name
    if body.parent_id is not None:
        org.parent_id = body.parent_id
    if body.code is not None:
        org.code = body.code
    await db.commit()
    return ok({"id": org.id})


@router.delete("/orgs/{org_id}")
async def delete_org(org_id: int, user: CurrentUser, db: DbSession) -> dict[str, Any]:
    require_roles(user, "admin")
    org = await db.get(Org, org_id)
    if org is None or org.deleted_at is not None:
        raise AppError(ErrorCode.NOT_FOUND, "组织不存在", http_status=404)
    org.deleted_at = utcnow_naive()
    await db.commit()
    return ok({"deleted": True})


# ---------- Users ----------


class UserCreate(BaseModel):
    name: str
    role: str
    org_id: int | None = None
    wecom_userid: str | None = None
    mobile: str | None = None


class UserPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    org_id: int | None = None
    status: int | None = None
    mobile: str | None = None


class AccountCreate(BaseModel):
    login_name: str
    password: str


@router.get("/users")
async def list_users(
    user: CurrentUser,
    db: DbSession,
    org_id: int | None = None,
    role: str | None = None,
    keyword: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
) -> dict[str, Any]:
    require_roles(user, "admin", "regional")
    p, ps = clamp_page(page, page_size)
    q = select(AppUser).where(AppUser.deleted_at.is_(None))
    if org_id is not None:
        q = q.where(AppUser.org_id == org_id)
    if role:
        q = q.where(AppUser.role == role)
    if keyword:
        q = q.where(
            or_(AppUser.name.ilike(f"%{keyword}%"), AppUser.mobile.ilike(f"%{keyword}%"))
        )
    if user["role"] == "regional" and user.get("org_id"):
        q = q.where(AppUser.org_id == user["org_id"])

    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(q.order_by(AppUser.id).offset((p - 1) * ps).limit(ps))
    ).scalars().all()
    items = [
        {
            "id": u.id,
            "name": u.name,
            "role": u.role,
            "org_id": u.org_id,
            "mobile": u.mobile,
            "status": u.status,
            "wecom_userid": u.wecom_userid,
        }
        for u in rows
    ]
    return ok({"items": items, **page_meta(p, ps, total)})


@router.post("/users")
async def create_user(
    body: UserCreate, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    require_roles(user, "admin", "regional")
    if body.role not in ("admin", "regional", "advisor"):
        raise AppError(ErrorCode.PARAM, "无效角色", http_status=400)
    if user["role"] == "regional" and body.role == "admin":
        raise AppError(ErrorCode.FORBIDDEN, "区域主管不能创建超管", http_status=403)
    row = AppUser(
        name=body.name,
        role=body.role,
        org_id=body.org_id or user.get("org_id"),
        wecom_userid=body.wecom_userid,
        mobile=body.mobile,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id})


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: int, body: UserPatch, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    require_roles(user, "admin", "regional")
    row = await db.get(AppUser, user_id)
    if row is None or row.deleted_at is not None:
        raise AppError(ErrorCode.NOT_FOUND, "用户不存在", http_status=404)
    if body.name is not None:
        row.name = body.name
    if body.role is not None:
        row.role = body.role
    if body.org_id is not None:
        row.org_id = body.org_id
    if body.status is not None:
        row.status = body.status
    if body.mobile is not None:
        row.mobile = body.mobile
    await db.commit()
    return ok({"id": row.id})


@router.post("/users/{user_id}/account")
async def create_account(
    user_id: int, body: AccountCreate, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    require_roles(user, "admin")
    target = await db.get(AppUser, user_id)
    if target is None or target.deleted_at is not None:
        raise AppError(ErrorCode.NOT_FOUND, "用户不存在", http_status=404)
    existing = (
        await db.execute(select(AdminAccount).where(AdminAccount.user_id == user_id))
    ).scalar_one_or_none()
    if existing:
        raise AppError(ErrorCode.CONFLICT, "账号已存在", http_status=409)
    acc = AdminAccount(
        user_id=user_id,
        login_name=body.login_name,
        password_hash=hash_password(body.password),
    )
    db.add(acc)
    await db.commit()
    return ok({"user_id": user_id, "login_name": body.login_name})


# ---------- Customers ----------


class CustomerPatch(BaseModel):
    parent_name: str | None = None
    student_name: str | None = None
    grade: str | None = None
    school: str | None = None
    stage: str | None = None
    owner_user_id: int | None = None
    org_id: int | None = None
    remark: str | None = None


class CsSummaryBody(BaseModel):
    summary_text: str


@router.get("/customers")
async def list_customers(
    user: CurrentUser,
    db: DbSession,
    keyword: str | None = None,
    grade: str | None = None,
    tag_id: int | None = None,
    owner_user_id: int | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
) -> dict[str, Any]:
    p, ps = clamp_page(page, page_size)
    q = select(Customer).where(Customer.deleted_at.is_(None))
    q = await apply_scope(q, user, db)
    if keyword:
        q = q.where(
            or_(
                Customer.parent_name.ilike(f"%{keyword}%"),
                Customer.student_name.ilike(f"%{keyword}%"),
            )
        )
    if grade:
        q = q.where(Customer.grade == grade)
    if owner_user_id:
        q = q.where(Customer.owner_user_id == owner_user_id)
    if tag_id:
        q = q.where(
            Customer.id.in_(
                select(CustomerTag.customer_id).where(CustomerTag.tag_id == tag_id)
            )
        )

    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(
            q.order_by(Customer.id.desc()).offset((p - 1) * ps).limit(ps)
        )
    ).scalars().all()

    items = []
    for c in rows:
        owner = await db.get(AppUser, c.owner_user_id) if c.owner_user_id else None
        tags = (
            await db.execute(
                select(TagDef.name)
                .join(CustomerTag, CustomerTag.tag_id == TagDef.id)
                .where(CustomerTag.customer_id == c.id)
            )
        ).scalars().all()
        draft = (
            await db.execute(
                select(ProfileDraft.id).where(
                    ProfileDraft.customer_id == c.id, ProfileDraft.status == "draft"
                ).limit(1)
            )
        ).scalar_one_or_none()
        confirmed = (
            await db.execute(
                select(CustomerProfile.id).where(CustomerProfile.customer_id == c.id)
            )
        ).scalar_one_or_none()
        profile_status = "confirmed" if confirmed and not draft else (
            "draft" if draft else "empty"
        )
        items.append(
            {
                "id": c.id,
                "parent_name": c.parent_name,
                "student_name": c.student_name,
                "grade": c.grade,
                "tags": list(tags),
                "owner_name": owner.name if owner else None,
                "profile_status": profile_status,
                "last_contact_at": c.last_contact_at.isoformat() + "Z"
                if c.last_contact_at
                else None,
            }
        )
    return ok({"items": items, **page_meta(p, ps, total)})


@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: int, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    customer = await assert_customer_in_scope(db, user, customer_id)
    confirmed = (
        await db.execute(
            select(CustomerProfile).where(CustomerProfile.customer_id == customer_id)
        )
    ).scalar_one_or_none()
    draft = (
        await db.execute(
            select(ProfileDraft)
            .where(ProfileDraft.customer_id == customer_id, ProfileDraft.status == "draft")
            .order_by(ProfileDraft.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    tags = (
        await db.execute(
            select(TagDef, CustomerTag)
            .join(CustomerTag, CustomerTag.tag_id == TagDef.id)
            .where(CustomerTag.customer_id == customer_id)
        )
    ).all()
    orders = (
        await db.execute(
            select(OrderRecord)
            .where(OrderRecord.customer_id == customer_id)
            .order_by(OrderRecord.id.desc())
        )
    ).scalars().all()
    messages = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.customer_id == customer_id)
            .order_by(ChatMessage.msg_time.desc())
            .limit(30)
        )
    ).scalars().all()
    cs = (
        await db.execute(
            select(CsSummary).where(CsSummary.customer_id == customer_id)
        )
    ).scalar_one_or_none()
    owner = await db.get(AppUser, customer.owner_user_id) if customer.owner_user_id else None

    return ok(
        {
            "customer": {
                "id": customer.id,
                "parent_name": customer.parent_name,
                "student_name": customer.student_name,
                "grade": customer.grade,
                "school": customer.school,
                "stage": customer.stage,
                "owner_user_id": customer.owner_user_id,
                "owner_name": owner.name if owner else None,
                "org_id": customer.org_id,
                "remark": customer.remark,
            },
            "profile": {
                "confirmed": _serialize_confirmed(confirmed),
                "draft": _serialize_draft(draft),
            },
            "tags": [{"id": t.id, "name": t.name, "customer_tag_id": ct.id} for t, ct in tags],
            "orders": [
                {
                    "id": o.id,
                    "external_order_no": o.external_order_no,
                    "title": o.title,
                    "amount": float(o.amount) if o.amount is not None else None,
                    "status": o.status,
                }
                for o in orders
            ],
            "recent_messages": [
                {
                    "id": m.id,
                    "direction": m.direction,
                    "content": m.content,
                    "msg_time": m.msg_time.isoformat() + "Z" if m.msg_time else None,
                }
                for m in messages
            ],
            "cs_summary": {"summary_text": cs.summary_text} if cs else None,
        }
    )


@router.patch("/customers/{customer_id}")
async def patch_customer(
    customer_id: int, body: CustomerPatch, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    customer = await assert_customer_in_scope(db, user, customer_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    await db.commit()
    return ok({"id": customer.id})


@router.put("/customers/{customer_id}/cs-summary")
async def put_cs_summary(
    customer_id: int, body: CsSummaryBody, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    await assert_customer_in_scope(db, user, customer_id)
    cs = (
        await db.execute(select(CsSummary).where(CsSummary.customer_id == customer_id))
    ).scalar_one_or_none()
    if cs is None:
        cs = CsSummary(
            customer_id=customer_id,
            summary_text=body.summary_text,
            updated_by=user["id"],
        )
        db.add(cs)
    else:
        cs.summary_text = body.summary_text
        cs.updated_by = user["id"]
    await db.commit()
    return ok({"customer_id": customer_id})


# ---------- Orders ----------


class OrderCreate(BaseModel):
    customer_id: int
    external_order_no: str | None = None
    title: str
    amount: float = 0
    status: str = "paid"
    paid_at: datetime | None = None


@router.get("/orders")
async def list_orders(
    user: CurrentUser,
    db: DbSession,
    customer_id: int | None = None,
    status: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
) -> dict[str, Any]:
    p, ps = clamp_page(page, page_size)
    q = (
        select(OrderRecord, Customer)
        .join(Customer, Customer.id == OrderRecord.customer_id)
        .where(Customer.deleted_at.is_(None))
    )
    # scope via customer
    scoped = await apply_scope(select(Customer.id).where(Customer.deleted_at.is_(None)), user, db)
    scoped_ids = (await db.execute(scoped)).scalars().all()
    q = q.where(OrderRecord.customer_id.in_(list(scoped_ids) or [-1]))
    if customer_id:
        await assert_customer_in_scope(db, user, customer_id)
        q = q.where(OrderRecord.customer_id == customer_id)
    if status:
        q = q.where(OrderRecord.status == status)

    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    rows = (
        await db.execute(q.order_by(OrderRecord.id.desc()).offset((p - 1) * ps).limit(ps))
    ).all()
    items = [
        {
            "id": o.id,
            "customer_id": o.customer_id,
            "parent_name": c.parent_name,
            "external_order_no": o.external_order_no,
            "title": o.title,
            "amount": float(o.amount) if o.amount is not None else None,
            "status": o.status,
        }
        for o, c in rows
    ]
    return ok({"items": items, **page_meta(p, ps, total)})


@router.post("/orders")
async def create_order(
    body: OrderCreate, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    await assert_customer_in_scope(db, user, body.customer_id)
    row = OrderRecord(
        customer_id=body.customer_id,
        external_order_no=body.external_order_no,
        title=body.title,
        amount=body.amount,
        status=body.status,
        paid_at=(body.paid_at.replace(tzinfo=None) if body.paid_at and body.paid_at.tzinfo else body.paid_at)
        or (utcnow_naive() if body.status == "paid" else None),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id})


# ---------- Tags ----------


class TagCreate(BaseModel):
    name: str
    description: str | None = None
    is_measurable: bool = True
    sop_text: str | None = None
    enabled: bool = True
    sort_order: int = 0


class TagPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    is_measurable: bool | None = None
    sop_text: str | None = None
    enabled: bool | None = None
    sort_order: int | None = None


@router.get("/tags/stats")
async def tag_stats(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    require_roles(user, "admin", "regional", "advisor")
    rows = (
        await db.execute(
            select(
                TagDef.id,
                TagDef.name,
                func.count(CustomerTag.id).label("customer_count"),
            )
            .outerjoin(CustomerTag, CustomerTag.tag_id == TagDef.id)
            .where(TagDef.deleted_at.is_(None))
            .group_by(TagDef.id, TagDef.name)
            .order_by(TagDef.sort_order, TagDef.id)
        )
    ).all()
    return ok(
        {
            "items": [
                {"tag_id": r.id, "name": r.name, "customer_count": int(r.customer_count)}
                for r in rows
            ]
        }
    )


@router.get("/tags")
async def list_tags(user: CurrentUser, db: DbSession) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(TagDef)
            .where(TagDef.deleted_at.is_(None))
            .order_by(TagDef.sort_order, TagDef.id)
        )
    ).scalars().all()
    counts = {
        r.tag_id: r.customer_count
        for r in (
            await db.execute(
                select(
                    CustomerTag.tag_id,
                    func.count(CustomerTag.id).label("customer_count"),
                ).group_by(CustomerTag.tag_id)
            )
        ).all()
    }
    return ok(
        {
            "items": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "sop_text": t.sop_text,
                    "enabled": t.enabled,
                    "is_measurable": t.is_measurable,
                    "sort_order": t.sort_order,
                    "customer_count": counts.get(t.id, 0),
                }
                for t in rows
            ]
        }
    )


@router.post("/tags")
async def create_tag(
    body: TagCreate, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    require_roles(user, "admin", "regional")
    row = TagDef(**body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id})


@router.patch("/tags/{tag_id}")
async def patch_tag(
    tag_id: int, body: TagPatch, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    require_roles(user, "admin", "regional")
    row = await db.get(TagDef, tag_id)
    if row is None or row.deleted_at is not None:
        raise AppError(ErrorCode.NOT_FOUND, "标签不存在", http_status=404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    await db.commit()
    return ok({"id": row.id})


# ---------- Script templates ----------


class ScriptTemplateCreate(BaseModel):
    scene: str
    stage: str | None = None
    title: str | None = None
    content: str
    enabled: bool = True


class ScriptTemplatePatch(BaseModel):
    scene: str | None = None
    stage: str | None = None
    title: str | None = None
    content: str | None = None
    enabled: bool | None = None


def _serialize_script(t: ScriptTemplate) -> dict[str, Any]:
    return {
        "id": t.id,
        "scene": t.scene,
        "stage": t.stage,
        "title": t.title,
        "content": t.content,
        "enabled": t.enabled,
        "created_at": t.created_at.isoformat() + "Z" if t.created_at else None,
        "updated_at": t.updated_at.isoformat() + "Z" if t.updated_at else None,
    }


@router.get("/script-templates")
async def list_script_templates(
    user: CurrentUser,
    db: DbSession,
    scene: str | None = None,
    stage: str | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    require_roles(user, "admin", "regional", "advisor")
    q = select(ScriptTemplate)
    if scene:
        q = q.where(ScriptTemplate.scene == scene)
    if stage is not None:
        q = q.where(ScriptTemplate.stage == stage) if stage else q.where(
            ScriptTemplate.stage.is_(None)
        )
    if enabled is not None:
        q = q.where(ScriptTemplate.enabled.is_(enabled))
    rows = (
        await db.execute(q.order_by(ScriptTemplate.scene, ScriptTemplate.id))
    ).scalars().all()
    return ok({"items": [_serialize_script(t) for t in rows]})


@router.post("/script-templates")
async def create_script_template(
    body: ScriptTemplateCreate, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    require_roles(user, "admin", "regional")
    if body.scene not in ("sales", "cs"):
        raise AppError(ErrorCode.PARAM, "scene 须为 sales/cs", http_status=400)
    if body.stage is not None and body.stage not in ("primary", "junior", "senior"):
        raise AppError(ErrorCode.PARAM, "无效 stage", http_status=400)
    row = ScriptTemplate(
        scene=body.scene,
        stage=body.stage,
        title=body.title,
        content=body.content,
        enabled=body.enabled,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id})


@router.patch("/script-templates/{template_id}")
async def patch_script_template(
    template_id: int, body: ScriptTemplatePatch, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    require_roles(user, "admin", "regional")
    row = await db.get(ScriptTemplate, template_id)
    if row is None:
        raise AppError(ErrorCode.NOT_FOUND, "话术模板不存在", http_status=404)
    data = body.model_dump(exclude_unset=True)
    if "scene" in data and data["scene"] not in ("sales", "cs"):
        raise AppError(ErrorCode.PARAM, "scene 须为 sales/cs", http_status=400)
    if "stage" in data and data["stage"] is not None and data["stage"] not in (
        "primary",
        "junior",
        "senior",
    ):
        raise AppError(ErrorCode.PARAM, "无效 stage", http_status=400)
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    return ok({"id": row.id})


@router.delete("/script-templates/{template_id}")
async def disable_script_template(
    template_id: int, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    """Soft disable via enabled=false."""
    require_roles(user, "admin", "regional")
    row = await db.get(ScriptTemplate, template_id)
    if row is None:
        raise AppError(ErrorCode.NOT_FOUND, "话术模板不存在", http_status=404)
    row.enabled = False
    await db.commit()
    return ok({"id": row.id, "enabled": False})


# ---------- AI adoption ----------

_ADOPTION_ACTIONS = (
    "reply_copy",
    "reply_adopt",
    "reply_reject",
    "reply_edit_adopt",
    "tag_recommend_confirm",
    "tag_recommend_reject",
    "tag_recommend_adopt",
)


@router.get("/ai/adoption")
async def ai_adoption(
    user: CurrentUser,
    db: DbSession,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    org_id: int | None = None,
    group_by: str | None = Query(default="advisor"),
) -> dict[str, Any]:
    require_roles(user, "admin", "regional")

    advisor_q = select(AppUser).where(
        AppUser.role == "advisor", AppUser.deleted_at.is_(None)
    )
    if user["role"] == "regional" and user.get("org_id"):
        advisor_q = advisor_q.where(AppUser.org_id == user["org_id"])
    if org_id is not None:
        if user["role"] != "admin":
            raise AppError(ErrorCode.FORBIDDEN, "仅超管可按 org_id 筛选", http_status=403)
        advisor_q = advisor_q.where(AppUser.org_id == org_id)
    advisors = {u.id: u for u in (await db.execute(advisor_q)).scalars().all()}
    advisor_ids = list(advisors.keys()) or [-1]

    q = select(EventLog).where(
        EventLog.action.in_(_ADOPTION_ACTIONS),
        EventLog.user_id.in_(advisor_ids),
    )
    if from_:
        start = from_.replace(tzinfo=None) if from_.tzinfo else from_
        q = q.where(EventLog.created_at >= start)
    if to:
        end = to.replace(tzinfo=None) if to.tzinfo else to
        q = q.where(EventLog.created_at <= end)
    events = (await db.execute(q)).scalars().all()

    shown_q = select(Suggestion).where(
        Suggestion.status.in_(("shown", "adopted", "rejected", "edit_adopted")),
        Suggestion.created_by_user.in_(advisor_ids),
    )
    if from_:
        start = from_.replace(tzinfo=None) if from_.tzinfo else from_
        shown_q = shown_q.where(Suggestion.created_at >= start)
    if to:
        end = to.replace(tzinfo=None) if to.tzinfo else to
        shown_q = shown_q.where(Suggestion.created_at <= end)
    shown_rows = (await db.execute(shown_q)).scalars().all()

    buckets: dict[tuple[Any, ...], dict[str, Any]] = {}

    def _ensure(user_id: int | None, day: str | None) -> dict[str, Any]:
        key: tuple[Any, ...] = (user_id, day) if group_by == "day" else (user_id,)
        if key not in buckets:
            adv = advisors.get(user_id) if user_id else None
            buckets[key] = {
                "user_id": user_id,
                "name": adv.name if adv else "unknown",
                "impressions": 0,
                "adopt": 0,
                "reject": 0,
                "edit_adopt": 0,
                "copy": 0,
                "tag_confirm": 0,
                "tag_reject": 0,
                "day": day if group_by == "day" else None,
            }
        return buckets[key]

    for e in events:
        day = e.created_at.date().isoformat() if e.created_at else None
        b = _ensure(e.user_id, day)
        if e.action == "reply_copy":
            b["copy"] += 1
        elif e.action == "reply_adopt":
            b["adopt"] += 1
        elif e.action == "reply_reject":
            b["reject"] += 1
        elif e.action == "reply_edit_adopt":
            b["edit_adopt"] += 1
        elif e.action in ("tag_recommend_confirm", "tag_recommend_adopt"):
            b["tag_confirm"] += 1
        elif e.action == "tag_recommend_reject":
            b["tag_reject"] += 1

    for s in shown_rows:
        day = s.created_at.date().isoformat() if s.created_at else None
        _ensure(s.created_by_user, day)["impressions"] += 1

    items = []
    for b in buckets.values():
        denom = b["adopt"] + b["edit_adopt"] + b["reject"]
        b["adoption_rate"] = (
            round((b["adopt"] + b["edit_adopt"]) / denom, 4) if denom else 0.0
        )
        items.append(b)
    items.sort(key=lambda x: (-(x["adopt"] + x["edit_adopt"]), x["user_id"] or 0))
    return ok({"items": items, "group_by": group_by or "advisor"})


# ---------- Dashboard ----------


@router.get("/dashboard/summary")
async def dashboard_summary(
    user: CurrentUser,
    db: DbSession,
    org_id: int | None = None,
) -> dict[str, Any]:
    q = select(Customer).where(Customer.deleted_at.is_(None))
    q = await apply_scope(q, user, db)
    if org_id is not None and user["role"] == "admin":
        q = q.where(Customer.org_id == org_id)
    customers = (await db.execute(q)).scalars().all()
    customer_ids = [c.id for c in customers] or [-1]

    lead = len(customers)
    tagged_intent = (
        await db.execute(
            select(func.count(func.distinct(CustomerTag.customer_id))).where(
                CustomerTag.customer_id.in_(customer_ids),
                CustomerTag.tag_id.in_(
                    select(TagDef.id).where(TagDef.name.in_(("高意向", "近期决策")))
                ),
            )
        )
    ).scalar_one()
    paid_orders = (
        await db.execute(
            select(OrderRecord).where(
                OrderRecord.customer_id.in_(customer_ids),
                OrderRecord.status == "paid",
            )
        )
    ).scalars().all()
    trial = sum(1 for o in paid_orders if o.title and "体验" in o.title)
    deal = len({o.customer_id for o in paid_orders})

    # advisor top by customer count in scope
    advisor_rows = (
        await db.execute(
            select(AppUser.id, AppUser.name, func.count(Customer.id))
            .outerjoin(Customer, Customer.owner_user_id == AppUser.id)
            .where(
                AppUser.role == "advisor",
                AppUser.deleted_at.is_(None),
                or_(Customer.id.is_(None), Customer.id.in_(customer_ids)),
            )
            .group_by(AppUser.id, AppUser.name)
            .order_by(func.count(Customer.id).desc())
            .limit(5)
        )
    ).all()

    renewal_rate = 0.63 if deal else 0.0  # MVP placeholder rate when deals exist

    return ok(
        {
            "funnel": {
                "lead": lead,
                "intent": int(tagged_intent or 0),
                "trial": trial,
                "deal": deal,
            },
            "renewal_rate": renewal_rate,
            "advisor_top": [
                {
                    "user_id": r.id,
                    "name": r.name,
                    "customers": int(r[2] or 0),
                    "deals": 0,
                    "score": min(100, 60 + int(r[2] or 0) * 5),
                }
                for r in advisor_rows
            ],
        }
    )
