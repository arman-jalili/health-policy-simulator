"""governance compliance persistence

Violation audit, provenance disclosures and the published institutional allowlist.

Revision ID: 0305_governance_compliance
Revises: 0304_simulation_pause_reason
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0305_governance_compliance"
down_revision: str | None = "0304_simulation_pause_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "governance_compliance_violation",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("invocation_id", sa.String(length=64), nullable=False),
        sa.Column("violation_class", sa.String(length=64), nullable=False),
        sa.Column("offending_span", sa.Text(), nullable=False),
        sa.Column("rewritten_span", sa.Text(), nullable=True),
        sa.Column("rule_id", sa.String(length=32), nullable=False),
        sa.Column("rule_version", sa.String(length=128), nullable=False),
        sa.Column("violation_hash", sa.String(length=64), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("violation_hash", name="uq_governance_violation_hash"),
    )
    op.create_index("ix_governance_violation_run", "governance_compliance_violation", ["run_id"])
    op.create_index(
        "ix_governance_violation_invocation", "governance_compliance_violation", ["invocation_id"]
    )
    op.create_index(
        "ix_governance_violation_class", "governance_compliance_violation", ["violation_class"]
    )
    op.create_table(
        "governance_compliance_provenance",
        sa.Column("position_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("argument_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("invocation_id", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("disclosed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("position_id", "version"),
        sa.UniqueConstraint("position_id", "version", name="uq_governance_provenance_version"),
    )
    op.create_table(
        "governance_compliance_allowlist",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("short_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.String(length=32), server_default="v1", nullable=False),
        sa.Column(
            "loaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("code"),
    )


def downgrade() -> None:
    op.drop_table("governance_compliance_allowlist")
    op.drop_table("governance_compliance_provenance")
    op.drop_index("ix_governance_violation_class", table_name="governance_compliance_violation")
    op.drop_index(
        "ix_governance_violation_invocation", table_name="governance_compliance_violation"
    )
    op.drop_index("ix_governance_violation_run", table_name="governance_compliance_violation")
    op.drop_table("governance_compliance_violation")
