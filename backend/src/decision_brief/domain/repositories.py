"""Domain-owned repository interface of DecisionBrief (contract frozen, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Domain-owned repository)

The table layout is out of bounds: adapters in ``infrastructure/repository/`` own column names. A
saved published version is never overwritten — ``save`` inserts a successor row.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.values import BriefId, RunId


@runtime_checkable
class DecisionBriefRepository(Protocol):
    """Persistence boundary of the aggregate, ordered by version per run."""

    async def get(self, brief_id: BriefId) -> DecisionBrief | None: ...

    async def save(self, brief: DecisionBrief) -> None: ...

    async def versions_for_run(self, run_id: RunId) -> list[DecisionBrief]: ...
