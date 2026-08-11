"""schedule_item

Revision ID: 0003_schedule_item
Revises: 0002_suggestion_script
Create Date: 2026-08-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_schedule_item"
down_revision: Union[str, Sequence[str], None] = "0002_suggestion_script"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedule_item",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
        sa.Column("owner_user_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=True),
        sa.Column(
            "sync_state",
            sa.String(length=16),
            nullable=False,
            server_default="none",
        ),
        sa.Column("external_cal_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=True),
        sa.Column("suggestion_id", sa.BigInteger(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_schedule_owner_time",
        "schedule_item",
        ["owner_user_id", "start_at"],
    )
    op.create_index(
        "idx_schedule_customer",
        "schedule_item",
        ["customer_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_schedule_customer", table_name="schedule_item")
    op.drop_index("idx_schedule_owner_time", table_name="schedule_item")
    op.drop_table("schedule_item")
