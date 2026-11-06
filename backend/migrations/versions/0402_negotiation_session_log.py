"""negotiation session event log

Append-only run log with a per-run sequence allocated by the store under an advisory lock (W9).

Revision ID: 0402_negotiation_session_log
Revises: 0401_negotiation_session
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0402_negotiation_session_log"
down_revision: str | None = "0401_negotiation_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "negotiation_session_event_log",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_negotiation_session_event_log"),
        sa.UniqueConstraint("run_id", "sequence", name="uq_negotiation_session_event_run_sequence"),
    )
    op.create_index(
        "ix_negotiation_session_event_log_run_id",
        "negotiation_session_event_log",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_negotiation_session_event_log_run_id",
        table_name="negotiation_session_event_log",
    )
    op.drop_table("negotiation_session_event_log")
