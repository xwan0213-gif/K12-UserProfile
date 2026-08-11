"""suggestion + script_template

Revision ID: 0002_suggestion_script
Revises: 0001_init_mvp
Create Date: 2026-08-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_suggestion_script"
down_revision: Union[str, Sequence[str], None] = "0001_init_mvp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "suggestion",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("scene", sa.String(length=16), nullable=True),
        sa.Column(
            "content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column("ai_job_id", sa.BigInteger(), nullable=True),
        sa.Column("created_by_user", sa.BigInteger(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_suggestion_customer",
        "suggestion",
        ["customer_id", "type", "created_at"],
    )

    op.create_table(
        "script_template",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scene", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=128), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "CREATE INDEX idx_script_scene ON script_template (scene, stage) "
        "WHERE enabled = true"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_script_scene")
    op.drop_table("script_template")
    op.drop_index("idx_suggestion_customer", table_name="suggestion")
    op.drop_table("suggestion")
