from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Org(Base):
    __tablename__ = "org"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("org.id"))
    code: Mapped[str | None] = mapped_column(String(64), unique=True)
    deleted_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (Index("idx_app_user_org", "org_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    wecom_userid: Mapped[str | None] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    mobile: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    org_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("org.id"))
    remind_pref: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class AdminAccount(Base):
    __tablename__ = "admin_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("app_user.id"), unique=True, nullable=False
    )
    login_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class Customer(Base):
    __tablename__ = "customer"
    __table_args__ = (
        Index("idx_customer_owner", "owner_user_id"),
        Index("idx_customer_org", "org_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    parent_name: Mapped[str | None] = mapped_column(String(64))
    student_name: Mapped[str | None] = mapped_column(String(64))
    grade: Mapped[str | None] = mapped_column(String(32))
    school: Mapped[str | None] = mapped_column(String(128))
    stage: Mapped[str | None] = mapped_column(String(16))
    owner_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("app_user.id")
    )
    org_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("org.id"))
    remark: Mapped[str | None] = mapped_column(Text)
    last_contact_at: Mapped[datetime | None] = mapped_column()
    deleted_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class CustomerProfile(Base):
    __tablename__ = "customer_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customer.id"), unique=True, nullable=False
    )
    basic_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    study_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    prefer_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    timeline: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    sources: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    version: Mapped[int] = mapped_column(Integer, default=1)
    confirmed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("app_user.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class ProfileDraft(Base):
    __tablename__ = "profile_draft"
    __table_args__ = (Index("idx_profile_draft_customer", "customer_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customer.id"), nullable=False
    )
    basic_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    study_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    prefer_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    timeline: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    field_status: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    sources: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    ai_job_id: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[str] = mapped_column(String(16), default="ai")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class TagDef(Base):
    __tablename__ = "tag_def"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_measurable: Mapped[bool] = mapped_column(Boolean, default=True)
    sop_text: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class CustomerTag(Base):
    __tablename__ = "customer_tag"
    __table_args__ = (
        UniqueConstraint("customer_id", "tag_id", name="uq_customer_tag"),
        Index("idx_customer_tag_tag", "tag_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customer.id"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tag_def.id"), nullable=False)
    source: Mapped[str | None] = mapped_column(String(16))
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OrderRecord(Base):
    __tablename__ = "order_record"
    __table_args__ = (Index("idx_order_customer", "customer_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customer.id"), nullable=False
    )
    external_order_no: Mapped[str | None] = mapped_column(String(64), unique=True)
    title: Mapped[str | None] = mapped_column(String(128))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str | None] = mapped_column(String(16))
    paid_at: Mapped[datetime | None] = mapped_column()
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_message"
    __table_args__ = (Index("idx_chat_customer_time", "customer_id", "msg_time"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customer.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    msg_type: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    asr_text: Mapped[str | None] = mapped_column(Text)
    msg_time: Mapped[datetime] = mapped_column(nullable=False)
    external_msg_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CsSummary(Base):
    __tablename__ = "cs_summary"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customer.id"), unique=True, nullable=False
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EventLog(Base):
    __tablename__ = "event_log"
    __table_args__ = (
        Index("idx_event_user_time", "user_id", "created_at"),
        Index("idx_event_action_time", "action", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("app_user.id"))
    customer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("customer.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(32))
    ref_id: Mapped[int | None] = mapped_column(BigInteger)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AiJob(Base):
    __tablename__ = "ai_job"
    __table_args__ = (Index("idx_ai_job_customer", "customer_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("customer.id"))
    task_type: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    request: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result_ref_type: Mapped[str | None] = mapped_column(String(32))
    result_ref_id: Mapped[int | None] = mapped_column(BigInteger)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    started_at: Mapped[datetime | None] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
