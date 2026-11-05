"""bootstrap

Phase 0 bootstrap (see .pi/architecture/implementation-roadmap.md):
- enables pgvector and pg_trgm for later phases
- creates the shared outbox and audit tables
- no context-owned tables yet

Chosen table naming follows ADR-002: ``<context_snake>_<entity>`` so ownership is visible in
every table name. Extensions are created here once because every later revision depends on
them; the downgrade intentionally leaves them in place (dropping ``vector`` would cascade into
later revisions and requires superuser rights on managed databases).

Revision ID: 0000_bootstrap
Revises:
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0000_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "shared_event_outbox",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column(
            "sequence",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_id", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "payload_schema_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_shared_event_outbox"),
        sa.UniqueConstraint("sequence", name="uq_shared_event_outbox_sequence"),
    )
    op.create_index(
        "ix_shared_event_outbox_event_name",
        "shared_event_outbox",
        ["event_name"],
    )
    op.create_index(
        "ix_shared_event_outbox_status_available_at",
        "shared_event_outbox",
        ["status", "available_at"],
    )
    op.create_index(
        "ix_shared_event_outbox_aggregate_type_aggregate_id",
        "shared_event_outbox",
        ["aggregate_type", "aggregate_id"],
    )

    op.create_table(
        "shared_audit",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column(
            "outcome",
            sa.String(length=16),
            server_default=sa.text("'success'"),
            nullable=False,
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shared_audit"),
    )
    op.create_index("ix_shared_audit_occurred_at", "shared_audit", ["occurred_at"])
    op.create_index("ix_shared_audit_action", "shared_audit", ["action"])
    op.create_index(
        "ix_shared_audit_resource_type_resource_id",
        "shared_audit",
        ["resource_type", "resource_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shared_audit_resource_type_resource_id",
        table_name="shared_audit",
    )
    op.drop_index("ix_shared_audit_action", table_name="shared_audit")
    op.drop_index("ix_shared_audit_occurred_at", table_name="shared_audit")
    op.drop_table("shared_audit")

    op.drop_index(
        "ix_shared_event_outbox_aggregate_type_aggregate_id",
        table_name="shared_event_outbox",
    )
    op.drop_index(
        "ix_shared_event_outbox_status_available_at",
        table_name="shared_event_outbox",
    )
    op.drop_index("ix_shared_event_outbox_event_name", table_name="shared_event_outbox")
    op.drop_table("shared_event_outbox")

    # Extensions are intentionally retained: they are database-level capabilities required by
    # every later revision (pgvector HNSW for passage embeddings, pg_trgm for lexical search).
