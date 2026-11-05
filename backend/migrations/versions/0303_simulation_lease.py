"""simulation orchestration worker leases

Adds a lease expiry so a RUNNING job left by a dead worker is reclaimable.

Revision ID: 0303_simulation_lease
Revises: 0302_simulation_orchestration
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0303_simulation_lease"
down_revision: str | None = "0302_simulation_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulation_orchestration_job",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulation_orchestration_job", "lease_expires_at")
