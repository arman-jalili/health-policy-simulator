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
from consensus_analysis.domain.events import (
    DomainEvent,
    ImpactAssessed,
    ScenarioDefined,
)
from consensus_analysis.domain.values import (
    BaselineRef,
    Horizon,
    LogPosition,
    PackageId,
    ScenarioAssumption,
    ScenarioId,
    UncertaintyLabel,
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
        scenario = cls(
            id=scenario_id,
            package_id=package_id,
            baseline=baseline,
            horizon=horizon,
            log_position=log_position,
            assumptions=tuple(assumptions),
        )
        scenario.events.append(
            ScenarioDefined(
                scenario_id=scenario_id,
                baseline=baseline.label,
                horizon=horizon.years,
                assumption_count=len(scenario.assumptions),
            )
        )
        return scenario

    def assess(self, assessment: ImpactAssessment) -> None:
        """Attach an assessment that references this scenario and its package (invariant 9)."""
        if assessment.scenario_id != self.id:
            raise ValueError(
                "ImpactAssessment must reference the scenario it is attached to "
                f"({assessment.scenario_id!r} != {self.id!r})"
            )
        if assessment.package_id != self.package_id:
            raise ValueError(
                "ImpactAssessment must reference this scenario's package "
                f"({assessment.package_id!r} != {self.package_id!r})"
            )
        self.assessments = (*self.assessments, assessment)
        counts: dict[str, int] = {}
        for figure in assessment.figures:
            counts[figure.basis.kind.value] = counts.get(figure.basis.kind.value, 0) + 1
        certainty = assessment.figures[0].label if assessment.figures else None
        self.events.append(
            ImpactAssessed(
                scenario_id=self.id,
                basis_counts=counts,
                uncertainty=certainty or UncertaintyLabel.ASSUMED,
            )
        )

    def drain_events(self) -> tuple[DomainEvent, ...]:
        """Return and clear the pending events for the outbox in the saving transaction."""
        drained = tuple(self.events)
        self.events.clear()
        return drained
