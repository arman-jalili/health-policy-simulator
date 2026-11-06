"""negotiation session persistence

Aggregate snapshot plus the child tables named by the module contract. The snapshot is authoritative
for replay (the domain owns its shape); child rows exist so reports can query without parsing JSONB.

Revision ID: 0401_negotiation_session
Revises: 0305_governance_compliance
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0401_negotiation_session"
down_revision: str | None = "0305_governance_compliance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = postgresql.JSONB(astext_type=sa.Text())


def _id(name: str, table: str) -> sa.Column:
    return sa.Column(name, sa.String(length=64), primary_key=True)


def upgrade() -> None:
    op.create_table(
        "negotiation_session_run",
        _id("id", "run"),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("round_cap", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSON, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "negotiation_session_mandate",
        _id("id", "mandate"),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "negotiation_session_round",
        _id("id", "round"),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "negotiation_session_position",
        _id("id", "position"),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "negotiation_session_argument",
        _id("id", "argument"),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "negotiation_session_conflict",
        _id("id", "conflict"),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "negotiation_session_coalition",
        _id("id", "coalition"),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "negotiation_session_coalition_offer",
        _id("id", "coalition_offer"),
        sa.Column("coalition_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "negotiation_session_round_learning",
        _id("id", "round_learning"),
        sa.Column("run_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("payload", JSON, nullable=False),
    )


def downgrade() -> None:
    for table in (
        "negotiation_session_round_learning",
        "negotiation_session_coalition_offer",
        "negotiation_session_coalition",
        "negotiation_session_conflict",
        "negotiation_session_argument",
        "negotiation_session_position",
        "negotiation_session_round",
        "negotiation_session_mandate",
        "negotiation_session_run",
    ):
        op.drop_table(table)
