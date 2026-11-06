"""decision brief artefacts

Immutable versions with their section, citation and rejected-proposal rows. The aggregate snapshot
is authoritative for reproduction; the child tables make citations queryable.

Revision ID: 0502_decision_brief
Revises: 0501_consensus_analysis
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0502_decision_brief"
down_revision: str | None = "0501_consensus_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "decision_brief_brief",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("snapshot", JSON, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_decision_brief_brief"),
        sa.UniqueConstraint("run_id", "version", name="uq_decision_brief_run_version"),
    )
    op.create_index("ix_decision_brief_brief_run_id", "decision_brief_brief", ["run_id"])
    for table in (
        "decision_brief_section",
        "decision_brief_cited_statement",
        "decision_brief_citation",
        "decision_brief_rejected_proposal",
    ):
        op.create_table(
            table,
            sa.Column("id", sa.String(length=96), nullable=False),
            sa.Column("brief_id", sa.String(length=64), nullable=False),
            sa.Column("ordinal", sa.Integer(), nullable=True),
            sa.Column("payload", JSON, nullable=False),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
        )
        op.create_index(f"ix_{table}_brief_id", table, ["brief_id"])


def downgrade() -> None:
    for table in (
        "decision_brief_citation",
        "decision_brief_cited_statement",
        "decision_brief_section",
        "decision_brief_rejected_proposal",
        "decision_brief_brief",
    ):
        if table == "decision_brief_brief":
            op.drop_index("ix_decision_brief_brief_run_id", table_name=table)
        else:
            op.drop_index(f"ix_{table}_brief_id", table_name=table)
        op.drop_table(table)
