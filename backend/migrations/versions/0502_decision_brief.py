"""decision brief artefacts (reserved)

Owned by the `decision-brief` epic. Published briefs are immutable versions, so the tables carry
identity and citation rows, not free-form JSON blobs.

Tables: ``decision_brief_brief``, ``_section``, ``_cited_statement``, ``_citation``,
``_rejected_proposal``.

Revision ID: 0502_decision_brief
Revises: 0501_consensus_analysis
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0502_decision_brief"
down_revision: str | None = "0501_consensus_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Populate with the decision brief tables."""


def downgrade() -> None:
    """Drop the decision brief tables."""
