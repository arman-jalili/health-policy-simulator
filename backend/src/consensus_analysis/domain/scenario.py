"""``Scenario`` aggregate root (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Aggregate State, invariant 9)

A scenario is the counterfactual a figure belongs to. It is defined before any figure exists, and
each assessment it holds references exactly one package and one scenario, so a headline number can
never be orphaned from the comparison that produced it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from consensus_analysis.domain.entities import ImpactAssessment
from consensus_analysis.domain.events import DomainEvent
from consensus_analysis.domain.values import (
    BaselineRef,
    Horizon,
    LogPosition,
    PackageId,
    ScenarioAssumption,
    ScenarioId,
)


@dataclass
class Scenario:
    """Counterfactual: package measures against a baseline and a horizon."""

    id: ScenarioId
    package_id: PackageId
    baseline: BaselineRef
    horizon: Horizon
    log_position: LogPosition
    assumptions: tuple[ScenarioAssumption, ...] = ()
    assessments: tuple[ImpactAssessment, ...] = ()
    events: list[DomainEvent] = field(default_factory=list)

    @classmethod
    def define(
        cls,
        *,
        scenario_id: ScenarioId,
        package_id: PackageId,
        baseline: BaselineRef,
        horizon: Horizon,
        log_position: LogPosition,
        assumptions: Sequence[ScenarioAssumption] = (),
    ) -> Scenario:
        """Define the counterfactual before any figure is estimated."""
        raise NotImplementedError("Scenario.define is implemented by issue #313")

    def assess(self, assessment: ImpactAssessment) -> None:
        """Attach an assessment that references this scenario and its package (invariant 9)."""
        raise NotImplementedError("Scenario.assess is implemented by issue #313")

    def drain_events(self) -> tuple[DomainEvent, ...]:
        """Return and clear the pending events for the outbox in the saving transaction."""
        raise NotImplementedError("Scenario.drain_events is implemented by issue #313")
