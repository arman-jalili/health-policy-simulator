"""Frozen domain-event payloads of ConsensusAnalysis (ADR-003, ADR-008, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Domain Events)

Event names are past-tense immutable facts about derived artefacts. Payloads carry ids plus the
minimum a consumer needs; DecisionBrief re-reads the projection for detail. Three of these events
are audit-critical because they record refusals and dissent (ADR-008 triage):
``ConsensusBlockedByVeto``, ``MinorityPositionRecorded`` and ``UnbackedEstimateBlocked``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import ClassVar

from consensus_analysis.domain.values import (
    BasisKind,
    ComponentId,
    FeasibilityLevel,
    PackageId,
    ProposalClass,
    RunId,
    ScenarioId,
    StakeholderId,
    StanceSnapshot,
    TopicRef,
    UncertaintyLabel,
)


@dataclass(frozen=True, slots=True)
class ConsensusDetermined:
    """Consensus level derived from recorded stances (AC 2)."""

    name: ClassVar[str] = "ConsensusDetermined"
    run_id: RunId
    topic: TopicRef
    support: float
    threshold: float
    supporters: tuple[StakeholderId, ...]


@dataclass(frozen=True, slots=True)
class ConsensusBlockedByVeto:
    """A threshold was met but a blocking competence applies (AC 1, audit-critical)."""

    name: ClassVar[str] = "ConsensusBlockedByVeto"
    run_id: RunId
    topic: TopicRef
    proposal_class: ProposalClass
    holder_ids: tuple[StakeholderId, ...]


@dataclass(frozen=True, slots=True)
class MinorityPositionRecorded:
    """A dissenting stance was recorded with its holders (AC 8, audit-critical)."""

    name: ClassVar[str] = "MinorityPositionRecorded"
    run_id: RunId
    topic: TopicRef
    holders: tuple[StakeholderId, ...]
    objection_count: int


@dataclass(frozen=True, slots=True)
class UnresolvedConflictDeclared:
    """A conflict was still open when the run closed (AC 2)."""

    name: ClassVar[str] = "UnresolvedConflictDeclared"
    run_id: RunId
    topic: TopicRef
    positions: tuple[StanceSnapshot, ...]


@dataclass(frozen=True, slots=True)
class CompromisePackageComposed:
    """Accepted components combined and rejected proposals documented (AC 9)."""

    name: ClassVar[str] = "CompromisePackageComposed"
    package_id: PackageId
    component_ids: tuple[ComponentId, ...]
    rejected_count: int


@dataclass(frozen=True, slots=True)
class ScenarioDefined:
    """A baseline-versus-package scenario was defined before any figure existed."""

    name: ClassVar[str] = "ScenarioDefined"
    scenario_id: ScenarioId
    baseline: str
    horizon: int
    assumption_count: int


@dataclass(frozen=True, slots=True)
class ImpactAssessed:
    """Impacts were estimated for a package with basis and uncertainty (invariants 6, 7)."""

    name: ClassVar[str] = "ImpactAssessed"
    scenario_id: ScenarioId
    basis_counts: Mapping[str, int]
    uncertainty: UncertaintyLabel


@dataclass(frozen=True, slots=True)
class UnbackedEstimateBlocked:
    """A figure was refused for claiming a computed basis without inputs (AC 5, audit-critical)."""

    name: ClassVar[str] = "UnbackedEstimateBlocked"
    scenario_id: ScenarioId
    field: str
    claimed_basis: BasisKind


@dataclass(frozen=True, slots=True)
class FeasibilityRated:
    """Political, legal and administrative feasibility rated with basis (AC 10)."""

    name: ClassVar[str] = "FeasibilityRated"
    package_id: PackageId
    ratings: Mapping[str, FeasibilityLevel]
    blockers: tuple[StakeholderId, ...]


type DomainEvent = (
    ConsensusDetermined
    | ConsensusBlockedByVeto
    | MinorityPositionRecorded
    | UnresolvedConflictDeclared
    | CompromisePackageComposed
    | ScenarioDefined
    | ImpactAssessed
    | UnbackedEstimateBlocked
    | FeasibilityRated
)
