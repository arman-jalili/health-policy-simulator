"""Domain services of ConsensusAnalysis.

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Patterns & OOP Mapping)

``ConsensusRule`` is a Specification composite: ``NotVetoed`` precedes ``ThresholdMet``, and
``MajorityHolds`` only records a carried stance. Each rule is individually reportable, so a blocked
outcome can name the competence that blocked it instead of an opaque "no consensus".

``EstimateValidator``, ``IllustrativeValueGuard`` and ``FeasibilityGuard`` are guard services: they
exist to refuse one specific, expensive mistake (invariants 7, 8 and 10). They are stateless and
never load or save; the aggregate applies them inside its transaction.

Contract frozen in issue #305. Veto precedence, threshold evaluation and minority capture are
implemented here by issue #306 because ``ConsensusRecord.determine`` cannot satisfy its acceptance
criteria without them; the component issues (#309, #310, #316) deepen their proofs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from consensus_analysis.domain.entities import MajorityPosition, MinorityPosition, PackageComponent
from consensus_analysis.domain.errors import (
    IllustrativeValueRefused,
    MislabeledEstimate,
    UnbackedEstimate,
)
from consensus_analysis.domain.values import (
    BasisKind,
    ConsensusOutcome,
    ConsensusThreshold,
    DocumentedExample,
    EstimateBasis,
    EstimatedFigure,
    FeasibilityRating,
    ProposalClass,
    StakeholderId,
    StanceSnapshot,
    SupportLevel,
    UncertaintyLabel,
    VetoBlockedOutcome,
)


def _same_number(left: Decimal, right: Decimal) -> bool:
    """Compare two figures by value, ignoring how they were written down."""
    left_exponent = int(left.as_tuple().exponent)
    right_exponent = int(right.as_tuple().exponent)
    step = Decimal(1).scaleb(min(left_exponent, right_exponent))
    return left.quantize(step) == right.quantize(step)


def ordered(stances: Mapping[StakeholderId, StanceSnapshot]) -> tuple[StanceSnapshot, ...]:
    """Order stances by log position so every derivation is reproducible (roadmap W9)."""
    return tuple(
        sorted(
            stances.values(),
            key=lambda snapshot: (
                snapshot.log_position if snapshot.log_position is not None else -1,
                str(snapshot.stakeholder),
            ),
        )
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
        return tuple(
            sorted(
                (
                    stakeholder
                    for stakeholder, classes in vetoes.items()
                    if proposal_class in classes
                ),
                key=str,
            )
        )


@dataclass(frozen=True, slots=True)
class ThresholdMet:
    """Specification: the weighted support reaches the mandate threshold (AC 2)."""

    def is_satisfied_by(self, *, support_value: float, threshold: ConsensusThreshold) -> bool:
        """Return whether the support level satisfies the mandate threshold."""
        return support_value >= threshold.required_share


@dataclass(frozen=True, slots=True)
class MajorityHolds:
    """Specification: the recording of the stance carried by the weight-bearing stakeholders."""

    def majority_of(
        self,
        *,
        proposal: str,
        stances: Mapping[StakeholderId, StanceSnapshot],
    ) -> MajorityPosition:
        """Record the carried stance; it never upgrades a partial outcome to consensus.

        The supporters are the recorded holders that approve, in log order, and the support level is
        the weighted measure. Recording a majority with no supporters is refused by
        ``MajorityPosition.carry``: a "majority" nobody holds is the manufactured agreement this
        context exists to prevent.
        """
        supporters = tuple(
            snapshot.stakeholder
            for snapshot in ordered(stances)
            if snapshot.recorded and snapshot.supports
        )
        return MajorityPosition.carry(
            proposal=proposal,
            supporters=supporters,
            support=SupportLevel.weighted(stances),
        )


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
        """Return one position per dissenting stakeholder; none may be dropped.

        One position per stakeholder — not one per topic — is what makes "every disapproving
        stakeholder appears in a recorded minority position" checkable rather than aspirational.
        """
        stated = objections or {}
        positions: list[MinorityPosition] = []
        for snapshot in ordered(stances):
            if not (snapshot.recorded and snapshot.disapproves):
                continue
            reason = stated.get(snapshot.stakeholder, "").strip()
            positions.append(
                MinorityPosition(
                    holders=(snapshot.stakeholder,),
                    objections=(reason,) if reason else (),
                    proposal=proposal,
                )
            )
        return tuple(positions)


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
        """Evaluate the specifications in precedence order and return one outcome.

        Veto first (AC 1): a blocked class is never consensus, whatever the support was. Then the
        threshold (AC 2), then dissent. Nothing here invents agreement.
        """
        support = SupportLevel.weighted(stances)
        holders = self.veto.holders_for(proposal_class=proposal_class, vetoes=vetoes)
        if holders:
            return ConsensusOutcome.veto_blocked(
                VetoBlockedOutcome(proposal_class=proposal_class, holders=holders), support
            )
        if self.threshold.is_satisfied_by(support_value=support.value, threshold=threshold):
            return ConsensusOutcome.consensus(support)
        minority = MinorityCapture().capture(stances=stances)
        if minority:
            return ConsensusOutcome.partial(
                support, tuple(holder for position in minority for holder in position.holders)
            )
        return ConsensusOutcome.unresolved(support)


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
        """Refuse an unbacked basis (AC 5) or a label that misstates it (AC 6)."""
        if not figure.basis.is_backed():
            raise UnbackedEstimate(figure.field, figure.basis.kind.value)
        expected = self.label_for(figure.basis)
        if figure.label is not expected:
            raise MislabeledEstimate(
                figure.field,
                figure.basis.kind.value,
                figure.label.value,
                expected.value,
            )

    def label_for(self, basis: EstimateBasis) -> UncertaintyLabel:
        """Return the label a reader must see for this basis; assumed never renders computed.

        Four bases collapse onto three labels because a reader needs to know how much to trust the
        number, not which pipeline produced it: a reference figure is evidenced, a computation or a
        model is modelled, and an assumption — or a refusal to estimate — is assumed.
        """
        match basis.kind:
            case BasisKind.MEASURED:
                return UncertaintyLabel.EVIDENCED
            case BasisKind.DERIVED | BasisKind.MODELLED:
                return UncertaintyLabel.MODELLED
            case _:
                return UncertaintyLabel.ASSUMED


@dataclass(frozen=True, slots=True)
class IllustrativeValueGuard:
    """Guard: a documentation example can never be persisted as a run outcome (AC 7)."""

    def refuse(self, figure: EstimatedFigure, examples: Sequence[DocumentedExample]) -> None:
        """Raise ``IllustrativeValueRefused`` when the figure reproduces a documented example.

        The comparison is numeric, so ``22``, ``22.0`` and ``Decimal("22.00")`` are the same value:
        the failure this guard prevents is a demo number reappearing as a result, and its rendering
        is incidental. A coincidental match is indistinguishable from the defect, so it is refused
        and the example is named — the operator can correct the catalogue or the figure.
        """
        for example in examples:
            if _same_number(figure.value, example.value):
                raise IllustrativeValueRefused(figure.field, f"{example.value}", example.source)


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
