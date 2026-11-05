"""claim validation persistence

Claims, reference figures and contradiction findings. Aggregate payloads are JSONB so the domain
keeps ownership of their shape; measure keys are duplicated for equality lookups.

Revision ID: 0301_claim_validation
Revises: 0201_evidence_retrieval
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0301_claim_validation"
down_revision: str | None = "0201_evidence_retrieval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_validation_reference_figure",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("measure_key", sa.String(length=512), nullable=False),
        sa.Column("measure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("value", sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column("tier", sa.String(length=64), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_claim_validation_reference_figure"),
    )
    op.create_index(
        "ix_claim_validation_reference_figure_measure_key",
        "claim_validation_reference_figure",
        ["measure_key"],
    )

    op.create_table(
        "claim_validation_claim",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=32), nullable=False),
        sa.Column("measure_key", sa.String(length=512), nullable=True),
        sa.Column("measure", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("verification", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("review", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_claim_validation_claim"),
    )
    op.create_index(
        "ix_claim_validation_claim_measure_key",
        "claim_validation_claim",
        ["measure_key"],
    )

    op.create_table(
        "claim_validation_contradiction",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("claim_id_a", sa.String(length=64), nullable=False),
        sa.Column("claim_id_b", sa.String(length=64), nullable=False),
        sa.Column("measure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("delta", sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_claim_validation_contradiction"),
    )
    op.create_index(
        "ix_claim_validation_contradiction_claims",
        "claim_validation_contradiction",
        ["claim_id_a", "claim_id_b"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_claim_validation_contradiction_claims", table_name="claim_validation_contradiction"
    )
    op.drop_table("claim_validation_contradiction")
    op.drop_index("ix_claim_validation_claim_measure_key", table_name="claim_validation_claim")
    op.drop_table("claim_validation_claim")
    op.drop_index(
        "ix_claim_validation_reference_figure_measure_key",
        table_name="claim_validation_reference_figure",
    )
    op.drop_table("claim_validation_reference_figure")
