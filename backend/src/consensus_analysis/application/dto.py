"""Use-case results and ACL-facing records of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (API Endpoints)

Result DTOs mirror the wire schemas one-to-one so the router needs no business mapping. The ACL
record ``ReferenceFigureView`` is the local shape ClaimValidation figures arrive in: the domain
sees an enumerated ``DerivationInput``, never a verification verdict or a source document.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from consensus_analysis.domain.values import (
    ComponentId,
    ConsensusId,
    ConsensusOutcomeKind,
    DerivationInput,
    EstimateBasis,
    EstimateLimitation,
    FeasibilityRating,
    PackageId,
    PackageState,
    ProposalClass,
    ReferenceFigureId,
    RunId,
    ScenarioId,
    StakeholderId,
    StanceSnapshot,
    TopicRef,
    UncertaintyLabel,
)


@dataclass(frozen=True, slots=True)
class MinorityResult:
    """One recorded dissent as the API renders it."""

    holders: tuple[StakeholderId, ...]
    objections: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConsensusRecordResult:
    """One derived per-topic outcome with its support, threshold and documented dissent."""

    consensus_id: ConsensusId
    run_id: RunId
    topic: TopicRef
    proposal_class: ProposalClass
    outcome: ConsensusOutcomeKind
    support: float
    threshold: float
    supporters: tuple[StakeholderId, ...] = ()
    minorities: tuple[MinorityResult, ...] = ()
    blockers: tuple[StakeholderId, ...] = ()


@dataclass(frozen=True, slots=True)
class ConsensusResult:
    records: tuple[ConsensusRecordResult, ...] = ()


@dataclass(frozen=True, slots=True)
class UnresolvedConflictResult:
    topic: TopicRef
    positions: tuple[StanceSnapshot, ...] = ()


@dataclass(frozen=True, slots=True)
class UnresolvedConflictListResult:
    conflicts: tuple[UnresolvedConflictResult, ...] = ()


@dataclass(frozen=True, slots=True)
class ComposePackageResult:
    package_id: PackageId
    component_ids: tuple[ComponentId, ...] = ()
    rejected_count: int = 0
    state: PackageState = PackageState.DRAFT


@dataclass(frozen=True, slots=True)
class PackageSummaryResult:
    package_id: PackageId
    state: PackageState
    component_count: int = 0
    rejected_count: int = 0


@dataclass(frozen=True, slots=True)
class PackageListResult:
    packages: tuple[PackageSummaryResult, ...] = ()


@dataclass(frozen=True, slots=True)
class EstimatedFigureResult:
    """One impact figure with the basis, label and limitation it must always travel with."""

    field: str
    value: Decimal
    basis: EstimateBasis
    label: UncertaintyLabel
    limitation: EstimateLimitation | None = None


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario_id: ScenarioId
    package_id: PackageId
    figures: tuple[EstimatedFigureResult, ...] = ()
    feasibility: FeasibilityRating | None = None


@dataclass(frozen=True, slots=True)
class ComparisonEntryResult:
    """One ranked alternative with all three comparison dimensions present (AC 11)."""

    package_id: PackageId
    scenario_id: ScenarioId
    cost: Decimal | None
    acceptance: float
    feasibility: FeasibilityRating
    rank: int


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    entries: tuple[ComparisonEntryResult, ...] = ()


@dataclass(frozen=True, slots=True)
class RebuildResult:
    """Proof that a replay reproduced the persisted rows byte-identically (AC 4)."""

    run_id: RunId
    records: int
    digest: str


@dataclass(frozen=True, slots=True)
class RunClosedResult:
    """What the event subscriber derived; zero records is a valid, honest outcome."""

    run_id: RunId
    records: int


@dataclass(frozen=True, slots=True)
class ReferenceFigureView:
    """Local ACL shape of a ClaimValidation reference figure (enumerable derivation input)."""

    reference_figure_id: ReferenceFigureId
    value: Decimal
    unit: str
    source: str


@dataclass(frozen=True, slots=True)
class EstimateRequest:
    """What an estimation strategy is asked for; inputs are mandatory for computed bases."""

    scenario_id: ScenarioId
    field: str
    inputs: tuple[DerivationInput, ...] = ()
    assumed_value: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ModelledEstimate:
    """Model adapter return: a value, its limitation and the invocation that produced it."""

    value: Decimal
    limitation: EstimateLimitation
    invocation_id: str
