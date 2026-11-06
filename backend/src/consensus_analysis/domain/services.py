"""Domain services of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Patterns & OOP Mapping)

``ConsensusRule`` is a Specification composite: ``NotVetoed`` precedes ``ThresholdMet``, and
``MajorityHolds`` only records a carried stance. Each rule is individually reportable, so a blocked
outcome can name the competence that blocked it instead of an opaque "no consensus".

``EstimateValidator``, ``IllustrativeValueGuard`` and ``FeasibilityGuard`` are guard services: they
exist to refuse one specific, expensive mistake (invariants 7, 8 and 10). They are stateless and
never load or save; the aggregate applies them inside its transaction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from consensus_analysis.domain.entities import MajorityPosition, MinorityPosition, PackageComponent
from consensus_analysis.domain.values import (
    ConsensusOutcome,
    ConsensusThreshold,
    DocumentedExample,
    EstimateBasis,
    EstimatedFigure,
    FeasibilityRating,
    ProposalClass,
    StakeholderId,
    StanceSnapshot,
    UncertaintyLabel,
)


@dataclass(frozen=True, slots=True)
class NotVetoed:
    """Specification: no bound stakeholder holds a veto over the proposal class (AC 1)."""

    def holders_for(
        self,
        *,
        proposal_class: ProposalClass,
        vetoes: Mapping[StakeholderId, frozenset[ProposalClass]],
    ) -> tuple[StakeholderId, ...]:
        """Return every institution whose veto covers the class, in a stable order."""
        raise NotImplementedError("NotVetoed.holders_for is implemented by issue #309")


@dataclass(frozen=True, slots=True)
class ThresholdMet:
    """Specification: the weighted support reaches the mandate threshold (AC 2)."""

    def is_satisfied_by(self, *, support_value: float, threshold: ConsensusThreshold) -> bool:
        """Return whether the support level satisfies the mandate threshold."""
        raise NotImplementedError("ThresholdMet.is_satisfied_by is implemented by issue #310")


@dataclass(frozen=True, slots=True)
class MajorityHolds:
    """Specification: the recording of the stance carried by the weight-bearing stakeholders."""

    def majority_of(
        self,
        *,
        proposal: str,
        stances: Mapping[StakeholderId, StanceSnapshot],
    ) -> MajorityPosition:
        """Record the carried stance; it never upgrades a partial outcome to consensus."""
        raise NotImplementedError("MajorityHolds.majority_of is implemented by issue #316")


@dataclass(frozen=True, slots=True)
class MinorityCapture:
    """Entity recording: every disapproving stance becomes a minority position (AC 8)."""

    def capture(
        self,
        *,
        stances: Mapping[StakeholderId, StanceSnapshot],
        objections: Mapping[StakeholderId, str] | None = None,
        proposal: str = "",
    ) -> tuple[MinorityPosition, ...]:
        """Return one position per dissenting stakeholder; none may be dropped."""
        raise NotImplementedError("MinorityCapture.capture is implemented by issue #316")


@dataclass(frozen=True, slots=True)
class ConsensusRule:
    """Pure evaluation used by the aggregate: veto precedence, then threshold (AC 1, AC 2)."""

    veto: NotVetoed = field(default_factory=NotVetoed)
    threshold: ThresholdMet = field(default_factory=ThresholdMet)

    def evaluate(
        self,
        *,
        proposal_class: ProposalClass,
        stances: Mapping[StakeholderId, StanceSnapshot],
        threshold: ConsensusThreshold,
        vetoes: Mapping[StakeholderId, frozenset[ProposalClass]],
    ) -> ConsensusOutcome:
        """Evaluate the specifications in precedence order and return one outcome."""
        raise NotImplementedError("ConsensusRule.evaluate is implemented by issue #309")


@dataclass(frozen=True, slots=True)
class ComponentsCompatible:
    """Specification: two individually accepted components may be combined (invariant 5)."""

    def is_satisfied_by(self, *, left: PackageComponent, right: PackageComponent) -> bool:
        """Return whether the two components can appear in the same package."""
        raise NotImplementedError(
            "ComponentsCompatible.is_satisfied_by is implemented by issue #317"
        )


@dataclass(frozen=True, slots=True)
class EstimateValidator:
    """Guard: a computed basis without enumerated inputs is refused (invariants 6, 7)."""

    def validate(self, figure: EstimatedFigure) -> None:
        """Raise ``UnbackedEstimate`` when the claimed basis has no inputs (AC 5)."""
        raise NotImplementedError("EstimateValidator.validate is implemented by issue #313")

    def label_for(self, basis: EstimateBasis) -> UncertaintyLabel:
        """Return the label a reader must see for this basis; assumed never renders computed."""
        raise NotImplementedError("EstimateValidator.label_for is implemented by issue #314")


@dataclass(frozen=True, slots=True)
class IllustrativeValueGuard:
    """Guard: a documentation example can never be persisted as a run outcome (AC 7)."""

    def refuse(self, figure: EstimatedFigure, examples: Sequence[DocumentedExample]) -> None:
        """Raise ``IllustrativeValueRefused`` when the figure reproduces a documented example."""
        raise NotImplementedError("IllustrativeValueGuard.refuse is implemented by issue #315")


@dataclass(frozen=True, slots=True)
class FeasibilityGuard:
    """Guard: a feasible scenario may not name a veto holder as consenting (AC 10)."""

    def assert_consistent(
        self,
        *,
        rating: FeasibilityRating,
        consenting: Sequence[StakeholderId],
        vetoes: Mapping[StakeholderId, frozenset[ProposalClass]],
        proposal_class: ProposalClass,
    ) -> None:
        """Raise ``FeasibilityContradictsVeto`` when feasibility is asserted against a blocker."""
        raise NotImplementedError("FeasibilityGuard.assert_consistent is implemented by issue #318")
