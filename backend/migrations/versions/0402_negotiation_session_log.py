"""negotiation session event log (reserved)

Owned by the `negotiation-session` epic. Append-only run log with a per-run sequence allocated
by the store (roadmap W9). Pre-allocated to keep the revision chain linear across parallel epics.

Table: ``negotiation_session_event_log``.

Revision ID: 0402_negotiation_session_log
Revises: 0401_negotiation_session
Create Date: 2026-11-06

"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0402_negotiation_session_log"
down_revision: str | None = "0401_negotiation_session"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Populate with the append-only run log table."""


def downgrade() -> None:
    """Drop the run log table."""
