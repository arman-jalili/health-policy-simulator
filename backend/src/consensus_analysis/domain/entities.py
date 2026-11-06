"""Owned entities of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Entities and value objects)

These objects have identity inside their aggregate and are immutable once recorded: a majority, a
minority position and an impact assessment are facts about a closed run, not working state.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from consensus_analysis.domain.values import (
    AssessmentId,
    BasisKind,
    ComponentId,
    DerivationInput,
    EstimateBasis,
    EstimatedFigure,
    EstimateLimitation,
    FeasibilityRating,
    PackageId,
    RejectedProposalId,
    ScenarioId,
    StakeholderId,
    SupportLevel,
)

_BASIS_STRENGTH: dict[BasisKind, int] = {
    BasisKind.MEASURED: 0,
    BasisKind.DERIVED: 1,
    BasisKind.MODELLED: 2,
    BasisKind.ASSUMED: 3,
    BasisKind.NOT_ESTIMATED: 4,
}


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


def _weakest_basis(figures: Sequence[EstimatedFigure]) -> EstimateBasis:
    """Return the least trustworthy basis present, with every input the figures enumerated."""
    if not figures:
        return EstimateBasis(kind=BasisKind.NOT_ESTIMATED)
    weakest = max(figures, key=lambda figure: _BASIS_STRENGTH[figure.basis.kind]).basis
    inputs: list[DerivationInput] = []
    for figure in figures:
        for derivation_input in figure.basis.inputs:
            if derivation_input not in inputs:
                inputs.append(derivation_input)
    return EstimateBasis(kind=weakest.kind, inputs=tuple(inputs))


@dataclass(frozen=True, slots=True)
class MajorityPosition:
    """The stance carried by the weight-bearing stakeholders (invariant 3)."""

    proposal: str
    supporters: tuple[StakeholderId, ...]
    support: SupportLevel

    def __post_init__(self) -> None:
        _require_text(self.proposal, "MajorityPosition.proposal")

    @classmethod
    def carry(
        cls, *, proposal: str, supporters: Sequence[StakeholderId], support: SupportLevel
    ) -> MajorityPosition:
        """Record the carried stance of one topic (AC 2).

        No supporters means no majority: recording one anyway would manufacture the very
        agreement this context must never invent.
        """
        if not supporters:
            raise ValueError("MajorityPosition.carry requires at least one supporter")
        return cls(proposal=proposal, supporters=tuple(supporters), support=support)

    def covers(self, stakeholders: Sequence[StakeholderId]) -> bool:
        """Return whether every named institution appears among the supporters."""
        return set(stakeholders) <= set(self.supporters)


@dataclass(frozen=True, slots=True)
class MinorityPosition:
    """A dissenting stance with its holders and their reasons (invariant 4, AC 8)."""

    holders: tuple[StakeholderId, ...]
    objections: tuple[str, ...]
    proposal: str = ""

    def __post_init__(self) -> None:
        if not self.holders:
            raise ValueError("MinorityPosition.holders must name at least one institution")

    @classmethod
    def record(
        cls,
        *,
        holders: Sequence[StakeholderId],
        objections: Sequence[str] = (),
        proposal: str = "",
    ) -> MinorityPosition:
        """Record dissent so it cannot disappear from the derived result (AC 8)."""
        return cls(
            holders=tuple(holders),
            objections=tuple(reason.strip() for reason in objections if reason.strip()),
            proposal=proposal,
        )

    def covers(self, stakeholders: Sequence[StakeholderId]) -> bool:
        """Return whether every named institution appears among the holders."""
        return set(stakeholders) <= set(self.holders)


@dataclass(frozen=True, slots=True)
class PackageComponent:
    """One measure accepted individually before composition (invariant 5)."""

    id: ComponentId
    measure: str
    accepted_by: tuple[StakeholderId, ...] = ()
    summary: str = ""
    cost_eur: Decimal | None = None
    requires: tuple[ComponentId, ...] = ()
    conflicts_with: tuple[ComponentId, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.measure, "PackageComponent.measure")


@dataclass(frozen=True, slots=True)
class RejectedProposal:
    """A measure that did not reach support, documented as not carried (AC 9)."""

    id: RejectedProposalId
    measure: str
    support: SupportLevel
    reason: str
    holders: tuple[StakeholderId, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.measure, "RejectedProposal.measure")
        _require_text(self.reason, "RejectedProposal.reason")


@dataclass(frozen=True, slots=True)
class ImpactAssessment:
    """Per-scenario estimate with its basis and its limitation (invariants 6, 7, 9)."""

    id: AssessmentId
    scenario_id: ScenarioId
    package_id: PackageId
    basis: EstimateBasis
    figures: tuple[EstimatedFigure, ...] = field(default_factory=tuple)
    limitation: EstimateLimitation | None = None
    feasibility: FeasibilityRating | None = None

    @classmethod
    def assess(
        cls,
        *,
        scenario_id: ScenarioId,
        package_id: PackageId,
        figures: Sequence[EstimatedFigure],
        assessment_id: AssessmentId,
        limitation: EstimateLimitation | None = None,
        feasibility: FeasibilityRating | None = None,
    ) -> ImpactAssessment:
        """Assemble one assessment for exactly one scenario and one package (AC 5, AC 6).

        The assessment carries the weakest basis of its figures: a bundle is only as trustworthy as
        its least backed number, and stating that once prevents the headline from quoting the best
        one.
        """
        collected = tuple(figures)
        return cls(
            id=assessment_id,
            scenario_id=scenario_id,
            package_id=package_id,
            basis=_weakest_basis(collected),
            figures=collected,
            limitation=limitation,
            feasibility=feasibility,
        )
