"""record per-path ingestion outcomes and reasons

Issue #427: a run that reports only counters hides which path failed and why.

Revision ID: 0105_ingestion_run_outcomes
Revises: 0502_decision_brief
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0105_ingestion_run_outcomes"
down_revision: str | None = "0502_decision_brief"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_corpus_ingestion_run",
        sa.Column(
            "outcomes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("evidence_corpus_ingestion_run", "outcomes")
