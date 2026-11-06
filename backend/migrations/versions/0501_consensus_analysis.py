"""consensus analysis projections (reserved)

Owned by the `consensus-analysis` epic. Derived projection tables, rebuildable from the run log,
keyed by log position rather than insertion order (roadmap W9).

Tables: ``consensus_analysis_consensus_record``, ``_majority``, ``_minority``, ``_package``,
``_scenario``, ``_impact``.

Revision ID: 0501_consensus_analysis
Revises: 0402_negotiation_session_log
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0501_consensus_analysis"
down_revision: str | None = "0402_negotiation_session_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Populate with the consensus projection tables."""


def downgrade() -> None:
    """Drop the consensus projection tables."""
