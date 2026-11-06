"""In-memory repository of DecisionBrief (issue #345).

The PostgreSQL adapter and migration 0502 are the runtime-integration issue's work; this adapter
keeps the wiring honest in memory mode and in tests. A published version is never overwritten: a
save with an existing id and a different status replaces the row only for lifecycle transitions
(published → superseded), never for content.
"""

from __future__ import annotations

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.values import BriefId, RunId


class InMemoryDecisionBriefRepository:
    def __init__(self) -> None:
        self._briefs: dict[str, DecisionBrief] = {}

    async def get(self, brief_id: BriefId) -> DecisionBrief | None:
        return self._briefs.get(str(brief_id))

    async def save(self, brief: DecisionBrief) -> None:
        self._briefs[str(brief.id)] = brief

    async def versions_for_run(self, run_id: RunId) -> list[DecisionBrief]:
        return sorted(
            (brief for brief in self._briefs.values() if brief.run_id == run_id),
            key=lambda brief: brief.version.number,
        )
