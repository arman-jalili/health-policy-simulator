"""Frozen value vocabulary of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Entities and value objects)

Value objects are immutable and equal by value. Rule-bearing methods raise ``NotImplementedError``
naming the issue that implements them: their signatures are frozen now and may change only with a
new freeze entry.

The four estimation value objects — :class:`EstimateBasis`, :class:`DerivationInput`,
:class:`EstimateLimitation` and :class:`EstimateBasis`-carrying :class:`EstimatedFigure` — are the
provenance contract. A figure never travels without them (invariants 6 and 7).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import NewType

ConsensusId = NewType("ConsensusId", str)
"""Identity of one derived per-topic outcome (``cns_...``)."""

PackageId = NewType("PackageId", str)
"""Identity of one composed compromise package (``pkg_...``)."""

ScenarioId = NewType("ScenarioId", str)
"""Identity of one assessed counterfactual (``scn_...``)."""

AssessmentId = NewType("AssessmentId", str)
"""Identity of one impact assessment (``imp_...``)."""

RunId = NewType("RunId", str)
"""Closed simulation run the projection derives from (``run_...``)."""

StakeholderId = NewType("StakeholderId", str)
"""Institution identity as published by StakeholderModel (``stk_...``)."""

TopicRef = NewType("TopicRef", str)
"""Policy topic a record, conflict or package component is scoped to."""

ComponentId = NewType("ComponentId", str)
"""Identity of one individually accepted package component (``cmp_...``)."""

RejectedProposalId = NewType("RejectedProposalId", str)
"""Identity of one documented, not-carried proposal (``rjp_...``)."""

ReferenceFigureId = NewType("ReferenceFigureId", str)
"""ClaimValidation reference figure usable as a derivation input (``fig_...``)."""

LogPosition = NewType("LogPosition", int)
"""Zero-based position in the append-only run log (roadmap W9 allocation key)."""


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must be non-empty")


def _require_unit_interval(value: float, field_name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be within [0, 1]")


class ProposalClass(StrEnum):
    """Blockable class of proposal.

    A local mirror of the published StakeholderModel vocabulary: ``domain/`` may not reach into
    another context's layers, so the ACL in ``infrastructure/acl.py`` reconciles the two. A veto
    applies to a class, never to one proposal id.
    """

    STATUTORY_BENEFIT_CHANGE = "statutory_benefit_change"
    BUDGET_FRAME = "budget_frame"
    SERVICE_CATALOGUE = "service_catalogue"
    FEE_SCHEDULE = "fee_schedule"
    HOSPITAL_PLAN = "hospital_plan"
    OTHER = "other"


class Stance(StrEnum):
    """A recorded position towards a topic, replayed from the run log."""

    SUPPORT = "support"
    OPPOSE = "oppose"
    QUALIFY = "qualify"
    CONDITIONAL_ACCEPT = "conditional_accept"
    ABSTAIN = "abstain"


class ConsensusOutcomeKind(StrEnum):
    """The four admissible derived outcomes; ``consensus`` is only one of them."""

    CONSENSUS = "consensus"
    PARTIAL = "partial"
    VETO_BLOCKED = "veto_blocked"
    UNRESOLVED = "unresolved"


class BasisKind(StrEnum):
    """Provenance class of one figure. ``not_estimated`` is a refusal, not a zero."""

    MEASURED = "measured"
    DERIVED = "derived"
    MODELLED = "modelled"
    ASSUMED = "assumed"
    NOT_ESTIMATED = "not_estimated"


class UncertaintyLabel(StrEnum):
    """Stated basis of an estimate as rendered to a reader."""

    EVIDENCED = "evidenced"
    MODELLED = "modelled"
    ASSUMED = "assumed"


class DerivationInputKind(StrEnum):
    """What kind of recorded artefact a derived figure enumerates."""

    REFERENCE_FIGURE = "reference_figure"
    PASSAGE = "passage"
    TALLY = "tally"


class FeasibilityLevel(StrEnum):
    """Political, legal or administrative implementability of a package."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ComparisonDimension(StrEnum):
    """The three dimensions a comparison ranks on; all three are mandatory (AC 11)."""

    COST = "cost"
    ACCEPTANCE = "acceptance"
    FEASIBILITY = "feasibility"


class PackageState(StrEnum):
    """Lifecycle of a compromise package aggregate."""

    DRAFT = "draft"
    COMPOSED = "composed"
    ASSESSED = "assessed"
    PUBLISHED = "published"
    ABANDONED = "abandoned"


@dataclass(frozen=True, slots=True)
class ConsensusThreshold:
    """Support level required by the mandate, never a default quorum."""

    required_share: float
    label: str = "mandate_threshold"

    def __post_init__(self) -> None:
        if not 0.0 < self.required_share <= 1.0:
            raise ValueError("ConsensusThreshold.required_share must be within (0, 1]")
        _require_text(self.label, "ConsensusThreshold.label")

    @classmethod
    def from_mandate(
        cls, required_share: float, *, label: str = "mandate_threshold"
    ) -> ConsensusThreshold:
        """Build the threshold of one mandate; there is deliberately no default."""
        return cls(required_share=required_share, label=label)


@dataclass(frozen=True, slots=True)
class StanceSnapshot:
    """One stakeholder's recorded stance on one topic, with its log provenance.

    ``recorded`` is the history assertion (invariant 2): a snapshot whose stance is absent from the
    closed run log may never contribute to an outcome.
    """

    stakeholder: StakeholderId
    stance: Stance
    weight: float = 1.0
    recorded: bool = True
    log_position: LogPosition | None = None

    def __post_init__(self) -> None:
        _require_unit_interval(self.weight, "StanceSnapshot.weight")

    @property
    def supports(self) -> bool:
        """Return whether the stance counts as approval of the proposal."""
        return self.stance in (Stance.SUPPORT, Stance.CONDITIONAL_ACCEPT)

    @property
    def disapproves(self) -> bool:
        """Return whether the stance must appear in a recorded minority position (AC 8)."""
        return self.stance in (Stance.OPPOSE, Stance.QUALIFY)


@dataclass(frozen=True, slots=True)
class SupportLevel:
    """Weighted measure of approval, equal by value; never derived from head count alone."""

    value: float
    total_weight: float = 0.0

    def __post_init__(self) -> None:
        _require_unit_interval(self.value, "SupportLevel.value")
        if self.total_weight < 0.0:
            raise ValueError("SupportLevel.total_weight must be non-negative")

    @classmethod
    def weighted(cls, stances: Mapping[StakeholderId, StanceSnapshot]) -> SupportLevel:
        """Weight every recorded stance by negotiating power; unrecorded stances weigh nothing.

        An abstention expresses no position, so it leaves the denominator instead of counting
        against approval. A run where nobody expressed a position has zero support, never a
        silent 1.0.
        """
        supporting = 0.0
        total = 0.0
        for snapshot in stances.values():
            if not snapshot.recorded or snapshot.stance is Stance.ABSTAIN:
                continue
            total += snapshot.weight
            if snapshot.supports:
                supporting += snapshot.weight
        if total <= 0.0:
            return cls(value=0.0, total_weight=0.0)
        return cls(value=min(1.0, supporting / total), total_weight=total)

    def meets(self, threshold: ConsensusThreshold) -> bool:
        """Return whether this level satisfies the mandate threshold (AC 2)."""
        return self.value >= threshold.required_share


@dataclass(frozen=True, slots=True)
class VetoBlockedOutcome:
    """Proposal class that met the threshold but is blocked by a competence (AC 1)."""

    proposal_class: ProposalClass
    holders: tuple[StakeholderId, ...]

    def __post_init__(self) -> None:
        if not self.holders:
            raise ValueError(
                "VetoBlockedOutcome.holders must name at least one blocking institution"
            )


@dataclass(frozen=True, slots=True)
class UnresolvedConflict:
    """A conflict that is still open at run close, with the positions that remain apart."""

    topic: TopicRef
    positions: tuple[StanceSnapshot, ...]

    def __post_init__(self) -> None:
        if len(self.positions) < 2:
            raise ValueError("UnresolvedConflict.positions must contain at least two positions")


@dataclass(frozen=True, slots=True)
class ResolvedConflict:
    """A conflict closed inside the run log, kept so the record can explain its own history."""

    topic: TopicRef
    resolution: str
    holders: tuple[StakeholderId, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.resolution, "ResolvedConflict.resolution")


@dataclass(frozen=True, slots=True)
class ConsensusOutcome:
    """The derived result for one topic. A veto always wins over a support count (AC 1)."""

    kind: ConsensusOutcomeKind
    support: SupportLevel
    veto: VetoBlockedOutcome | None = None
    minorities: tuple[StakeholderId, ...] = ()

    @classmethod
    def consensus(cls, support: SupportLevel) -> ConsensusOutcome:
        """Threshold met and no veto applies."""
        return cls(kind=ConsensusOutcomeKind.CONSENSUS, support=support)

    @classmethod
    def partial(
        cls, support: SupportLevel, minorities: Sequence[StakeholderId]
    ) -> ConsensusOutcome:
        """Threshold not met: the outcome is partial plus the recorded minority (AC 2)."""
        return cls(
            kind=ConsensusOutcomeKind.PARTIAL,
            support=support,
            minorities=tuple(minorities),
        )

    @classmethod
    def veto_blocked(cls, veto: VetoBlockedOutcome, support: SupportLevel) -> ConsensusOutcome:
        """A blocking competence applies, whatever the support level was (AC 1)."""
        return cls(kind=ConsensusOutcomeKind.VETO_BLOCKED, support=support, veto=veto)

    @classmethod
    def unresolved(cls, support: SupportLevel) -> ConsensusOutcome:
        """No threshold and no terminal position; the conflict stays open."""
        return cls(kind=ConsensusOutcomeKind.UNRESOLVED, support=support)


@dataclass(frozen=True, slots=True)
class DerivationInput:
    """One enumerated input behind a computed figure (invariant 7)."""

    kind: DerivationInputKind
    reference_id: str
    description: str = ""

    def __post_init__(self) -> None:
        _require_text(self.reference_id, "DerivationInput.reference_id")


@dataclass(frozen=True, slots=True)
class EstimateLimitation:
    """What an estimate ignores, stated next to the figure rather than in a footnote."""

    statement: str
    ignored_factors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.statement, "EstimateLimitation.statement")


@dataclass(frozen=True, slots=True)
class EstimateBasis:
    """Provenance of a figure plus the inputs that back it.

    ``measured`` and ``derived`` require inputs; without inputs the basis must be ``assumed``
    (invariant 7, enforced by ``EstimateValidator``).
    """

    kind: BasisKind
    inputs: tuple[DerivationInput, ...] = ()

    def requires_inputs(self) -> bool:
        """Return whether this basis may only be claimed with enumerated inputs.

        ``measured`` and ``derived`` are computations, so they must enumerate what they computed
        from. ``modelled`` cites the metered invocation instead, and ``assumed`` is honest
        precisely because it claims no computation (invariant 7).
        """
        return self.kind in (BasisKind.MEASURED, BasisKind.DERIVED)

    def is_backed(self) -> bool:
        """Return whether the claimed basis is honest for the enumerated inputs (AC 5)."""
        if not self.requires_inputs():
            return True
        return bool(self.inputs)


@dataclass(frozen=True, slots=True)
class EstimatedFigure:
    """One impact number with its basis, its label and its limitation (invariants 6, 7)."""

    field: str
    value: Decimal
    basis: EstimateBasis
    label: UncertaintyLabel
    limitation: EstimateLimitation | None = None

    def __post_init__(self) -> None:
        _require_text(self.field, "EstimatedFigure.field")

    def is_computable(self) -> bool:
        """Return whether the figure may be rendered as a computed value (AC 6).

        Label and basis must agree and the basis must be backed: an assumed figure has no shape in
        which it can be presented as a calculation.
        """
        if self.label is UncertaintyLabel.ASSUMED:
            return False
        if self.basis.kind in (BasisKind.ASSUMED, BasisKind.NOT_ESTIMATED):
            return False
        return self.basis.is_backed()


@dataclass(frozen=True, slots=True)
class DocumentedExample:
    """A figure taken from documentation. It can never be persisted as a run outcome (AC 7)."""

    value: Decimal
    source: str
    description: str = ""

    def __post_init__(self) -> None:
        _require_text(self.source, "DocumentedExample.source")


@dataclass(frozen=True, slots=True)
class FeasibilityRating:
    """Political, legal and administrative implementability, each with its own basis."""

    political: FeasibilityLevel
    legal: FeasibilityLevel
    administrative: FeasibilityLevel
    basis: EstimateBasis
    blockers: tuple[StakeholderId, ...] = ()

    def is_fully_rated(self) -> bool:
        """Return whether all three dimensions were rated (AC 11 requires all three).

        ``unknown`` is an explicit "not rated", not a neutral default, so it fails the check.
        """
        levels = (self.political, self.legal, self.administrative)
        return all(level is not FeasibilityLevel.UNKNOWN for level in levels)


@dataclass(frozen=True, slots=True)
class BaselineRef:
    """What a scenario is compared against; named, never implied."""

    label: str
    reference: str = ""

    def __post_init__(self) -> None:
        _require_text(self.label, "BaselineRef.label")


@dataclass(frozen=True, slots=True)
class Horizon:
    """Period an impact estimate covers."""

    years: int
    description: str = ""

    def __post_init__(self) -> None:
        if self.years < 1:
            raise ValueError("Horizon.years must be at least 1")


@dataclass(frozen=True, slots=True)
class ScenarioAssumption:
    """A stated assumption behind a scenario, carrying the same provenance contract as a figure."""

    statement: str
    basis: EstimateBasis

    def __post_init__(self) -> None:
        _require_text(self.statement, "ScenarioAssumption.statement")
