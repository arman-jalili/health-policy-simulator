"""consensus analysis projections

Derived projection tables, rebuildable from the run log and keyed by log position.

Revision ID: 0501_consensus_analysis
Revises: 0402_negotiation_session_log
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0501_consensus_analysis"
down_revision: str | None = "0402_negotiation_session_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "consensus_analysis_consensus_record",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("log_position", sa.Integer(), nullable=False),
        sa.Column("payload", JSON, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_consensus_analysis_consensus_record"),
        sa.UniqueConstraint("run_id", "topic", name="uq_consensus_analysis_run_topic"),
    )
    op.create_index(
        "ix_consensus_analysis_consensus_record_run_id",
        "consensus_analysis_consensus_record",
        ["run_id"],
    )
    for table in ("majority", "minority", "package", "scenario", "impact"):
        name = f"consensus_analysis_{table}"
        op.create_table(
            name,
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("run_id", sa.String(length=64), nullable=True),
            sa.Column("parent_id", sa.String(length=64), nullable=True),
            sa.Column("payload", JSON, nullable=False),
            sa.PrimaryKeyConstraint("id", name=f"pk_{name}"),
        )
        op.create_index(f"ix_{name}_run_id", name, ["run_id"])


def downgrade() -> None:
    for table in ("impact", "scenario", "package", "minority", "majority"):
        name = f"consensus_analysis_{table}"
        op.drop_index(f"ix_{name}_run_id", table_name=name)
        op.drop_table(name)
    op.drop_index(
        "ix_consensus_analysis_consensus_record_run_id",
        table_name="consensus_analysis_consensus_record",
    )
    op.drop_table("consensus_analysis_consensus_record")
