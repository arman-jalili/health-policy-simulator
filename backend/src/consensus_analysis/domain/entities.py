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
    ComponentId,
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


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


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
        """Record the carried stance of one topic (AC 2)."""
        raise NotImplementedError("MajorityPosition.carry is implemented by issue #316")

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
        raise NotImplementedError("MinorityPosition.record is implemented by issue #316")

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
        limitation: EstimateLimitation | None = None,
        feasibility: FeasibilityRating | None = None,
    ) -> ImpactAssessment:
        """Assemble one assessment for exactly one scenario and one package (AC 5, AC 6)."""
        raise NotImplementedError("ImpactAssessment.assess is implemented by issue #313")
