"""negotiation session persistence (reserved)

Owned by the `negotiation-session` epic. The revision id and its position in the chain are
pre-allocated so that three module epics can run in parallel worktrees without producing
multiple alembic heads. Fill in ``upgrade()``/``downgrade()`` in place — do not re-point
``down_revision`` and do not create a sibling revision for this module.

Tables (per .pi/architecture/implementation-roadmap.md, Phase 4):
``negotiation_session_run``, ``_mandate``, ``_round``, ``_position``, ``_argument``,
``_conflict``, ``_coalition``, ``_coalition_offer``, ``_round_learning``.

Revision ID: 0401_negotiation_session
Revises: 0305_governance_compliance
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0401_negotiation_session"
down_revision: str | None = "0305_governance_compliance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Populate with the negotiation session tables."""


def downgrade() -> None:
    """Drop the negotiation session tables."""
