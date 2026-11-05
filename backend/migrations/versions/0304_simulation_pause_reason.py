"""simulation orchestration deferred pause reason

Stores the operator reason while a pause is waiting for the in-flight turn to commit.

Revision ID: 0304_simulation_pause_reason
Revises: 0303_simulation_lease
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0304_simulation_pause_reason"
down_revision: str | None = "0303_simulation_lease"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulation_orchestration_job",
        sa.Column("pause_reason", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulation_orchestration_job", "pause_reason")
