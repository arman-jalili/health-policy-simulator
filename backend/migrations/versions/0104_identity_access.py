"""identity access api keys

Roadmap Phase 1, migration ``0104``: the API-key store behind ``ApiKeyAdminPort`` and
``PrincipalPort`` (ADR-005). Only the salted SHA-256 hash and salt are persisted; plaintext keys are
returned once at creation and never stored.

Revision ID: 0104_identity_access
Revises: 0103_evidence_corpus_snapshots
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0104_identity_access"
down_revision: str | None = "0103_evidence_corpus_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_access_api_key",
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("salt", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("key_id", name="pk_identity_access_api_key"),
    )
    op.create_index(
        "ix_identity_access_api_key_key_hash",
        "identity_access_api_key",
        ["key_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_identity_access_api_key_key_hash", table_name="identity_access_api_key")
    op.drop_table("identity_access_api_key")
