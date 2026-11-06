"""Use-case result DTOs and read projections (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (API Endpoints, Domain Events)

Read models are projections over the aggregate or the run log; they carry ids and facts, never
ORM rows. Payloads that leave the process are JSON-serialisable shapes built by the HTTP layer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from negotiation_session.domain.values import (
    ArgumentId,
    ArgumentStance,
    CoalitionId,
    CoalitionOfferId,
    CoalitionOfferStatus,
    ConflictStatus,
    ConflictTopicId,
    EvidencePackId,
    InvocationId,
    LearningId,
    NegotiationPhase,
    PositionId,
    Proposal,
    RevisionReason,
    RunId,
    StakeholderId,
    StoppingConditionName,
    TargetRef,
    TopicRef,
)


@dataclass(frozen=True, slots=True)
class MandateResult:
    mandate_id: str
    question: str
    objective: str
    constraints: tuple[str, ...]
    round_cap: int
    stopping_conditions: tuple[StoppingConditionName, ...]
    mandate_hash: str


@dataclass(frozen=True, slots=True)
class BoundStakeholderResult:
    stakeholder_id: StakeholderId
    institution_name: str
    institution_code: str
    profile_version: str
    persona_version: str


@dataclass(frozen=True, slots=True)
class OpenSimulationRunResult:
    run_id: RunId
    phase: NegotiationPhase
    mandate: MandateResult
    bound: tuple[BoundStakeholderResult, ...]


@dataclass(frozen=True, slots=True)
class SimulationRunResult:
    run_id: RunId
    phase: NegotiationPhase
    round: int
    round_cap: int
    closed: bool
    bound_stakeholder_ids: tuple[StakeholderId, ...]
    open_position_ids: tuple[PositionId, ...]
    coalition_ids: tuple[CoalitionId, ...]


@dataclass(frozen=True, slots=True)
class PositionResult:
    position_id: PositionId
    run_id: RunId
    round: int
    stakeholder_id: StakeholderId
    topic: TopicRef
    stance: ArgumentStance
    proposal: Proposal
    evidence_ids: tuple[EvidencePackId, ...]
    supersedes: PositionId | None = None
    revision: RevisionReason | None = None


@dataclass(frozen=True, slots=True)
class ArgumentResult:
    argument_id: ArgumentId
    run_id: RunId
    round: int
    stakeholder_id: StakeholderId
    target: TargetRef
    stance: ArgumentStance
    evidence_ids: tuple[EvidencePackId, ...]
    unsupported: bool
    invocation_id: InvocationId | None = None


@dataclass(frozen=True, slots=True)
class ConflictTopicResult:
    conflict_id: ConflictTopicId
    run_id: RunId
    topic: TopicRef
    status: ConflictStatus
    stances: Mapping[StakeholderId, ArgumentStance]


@dataclass(frozen=True, slots=True)
class CoalitionOfferResult:
    offer_id: CoalitionOfferId
    invited_id: StakeholderId
    conditions: str
    status: CoalitionOfferStatus
    decline_reason: str | None = None


@dataclass(frozen=True, slots=True)
class CoalitionResult:
    coalition_id: CoalitionId
    run_id: RunId
    topic: TopicRef
    proposal: Proposal
    members: tuple[StakeholderId, ...]
    offers: tuple[CoalitionOfferResult, ...]


@dataclass(frozen=True, slots=True)
class LearningInsightResult:
    insight_type: str
    statement: str
    derived_from: tuple[ArgumentId, ...]
    round_number: int


@dataclass(frozen=True, slots=True)
class RoundLearningResult:
    learning_id: LearningId
    run_id: RunId
    round: int
    insights: tuple[LearningInsightResult, ...]


@dataclass(frozen=True, slots=True)
class RoundSummaryResult:
    round: int
    closed: bool
    argument_count: int
    abstention_count: int
    learning: RoundLearningResult | None


@dataclass(frozen=True, slots=True)
class StoppingConditionResult:
    name: StoppingConditionName
    fired: bool
    parameters: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CloseRoundResult:
    run_id: RunId
    round: int
    learning: RoundLearningResult
    stopping_condition: StoppingConditionResult


@dataclass(frozen=True, slots=True)
class HistoryEventResult:
    sequence: int
    event_type: str
    payload: Mapping[str, object]
    occurred_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReplayResult:
    run_id: RunId
    until_round: int | None
    events: tuple[HistoryEventResult, ...]
    state: SimulationRunResult


@dataclass(frozen=True, slots=True)
class ProgressEventResult:
    """SSE frame contract: ``event_id`` doubles as ``Last-Event-ID``."""

    event_id: str
    run_id: RunId
    sequence: int
    event_type: str
    payload: Mapping[str, object]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StakeholderSelectionResult:
    stakeholder_ids: tuple[StakeholderId, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class IntermediateSummaryResult:
    run_id: RunId
    round: int
    phase: NegotiationPhase
    consensus: str
    open_conflicts: tuple[TopicRef, ...]
    coalition_ids: tuple[CoalitionId, ...]
    argument_count: int
