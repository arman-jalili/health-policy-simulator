"""evidence retrieval packs

Frozen packs are stored as JSONB payloads keyed by pack id; the aggregate shape stays owned by the
domain. `claim` is duplicated for the latest-for-claim lookup.

Revision ID: 0201_evidence_retrieval
Revises: 0104_identity_access
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0201_evidence_retrieval"
down_revision: str | None = "0104_identity_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_retrieval_pack",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("claim", sa.String(length=2000), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evidence_retrieval_pack"),
    )
    op.create_index(
        "ix_evidence_retrieval_pack_claim_created_at",
        "evidence_retrieval_pack",
        ["claim", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidence_retrieval_pack_claim_created_at",
        table_name="evidence_retrieval_pack",
    )
    op.drop_table("evidence_retrieval_pack")
