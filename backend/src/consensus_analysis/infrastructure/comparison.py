"""Alternative ranking over the three mandatory dimensions (issue #319).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Acceptance Criteria 11)

Ranking is deliberately simple and total, so a comparison can be audited by hand: acceptance first
(political agreement dominates), then feasibility (an unimplementable package is worth less), then
cost (cheaper wins a tie). Every dimension is present by construction — the caller refuses an
incomplete alternative before it reaches this strategy.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from consensus_analysis.application.dto import ComparisonEntryResult
from consensus_analysis.domain.values import (
    ComparisonDimension,
    FeasibilityLevel,
    PackageId,
    ScenarioId,
)

_FEASIBILITY_ORDER: dict[FeasibilityLevel, int] = {
    FeasibilityLevel.LOW: 0,
    FeasibilityLevel.MEDIUM: 1,
    FeasibilityLevel.HIGH: 2,
    FeasibilityLevel.UNKNOWN: -1,
}


class LexicographicRanker:
    """Order alternatives by acceptance, then feasibility, then cost, and number them."""

    def rank(self, entries: Sequence[ComparisonEntryResult]) -> Sequence[ComparisonEntryResult]:
        """Return the alternatives ranked 1..n with all three dimensions preserved."""
        ordered = sorted(entries, key=_sort_key)
        return tuple(
            ComparisonEntryResult(
                package_id=PackageId(entry.package_id),
                scenario_id=ScenarioId(entry.scenario_id),
                cost=entry.cost,
                acceptance=entry.acceptance,
                feasibility=entry.feasibility,
                rank=position,
            )
            for position, entry in enumerate(ordered, start=1)
        )

    def dimensions(self) -> tuple[ComparisonDimension, ...]:
        """The dimensions this ranker uses; all three are required of every alternative."""
        return (
            ComparisonDimension.ACCEPTANCE,
            ComparisonDimension.FEASIBILITY,
            ComparisonDimension.COST,
        )


def _weakest_feasibility(entry: ComparisonEntryResult) -> int:
    rating = entry.feasibility
    return min(
        _FEASIBILITY_ORDER[level]
        for level in (rating.political, rating.legal, rating.administrative)
    )


def _sort_key(entry: ComparisonEntryResult) -> tuple[float, int, Decimal, str]:
    """Acceptance desc, feasibility desc, cost asc, scenario id asc as a total-order tiebreak."""
    return (
        -entry.acceptance,
        -_weakest_feasibility(entry),
        entry.cost if entry.cost is not None else Decimal("Infinity"),
        str(entry.scenario_id),
    )
