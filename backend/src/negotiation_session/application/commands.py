"""Use-case request DTOs (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (API Endpoints)

These are the only inputs application services accept. Evidence is passed as pack ids: the
service resolves them through the ACL, the domain never sees a retrieval type.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from negotiation_session.domain.entities import RoundLearning
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimStatement,
    ConflictStatus,
    EvidencePackId,
    InvocationId,
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
class TranslateQuestionToMandateRequest:
    question: str
    round_cap: int = 5
    constraints: tuple[str, ...] = ()
    stopping_conditions: tuple[StoppingConditionName, ...] = ()


@dataclass(frozen=True, slots=True)
class SelectRelevantStakeholdersRequest:
    question: str
    mandate_topics: tuple[TopicRef, ...] = ()
    limit: int = 12


@dataclass(frozen=True, slots=True)
class OpenSimulationRunRequest:
    question: str
    round_cap: int = 5
    stakeholder_ids: tuple[StakeholderId, ...] = ()


@dataclass(frozen=True, slots=True)
class SubmitInitialPositionRequest:
    run_id: RunId
    stakeholder_id: StakeholderId
    topic: TopicRef
    stance: ArgumentStance
    proposal: Proposal
    evidence_ids: tuple[EvidencePackId, ...] = ()


@dataclass(frozen=True, slots=True)
class TakeNegotiationTurnRequest:
    run_id: RunId
    stakeholder_id: StakeholderId
    target: TargetRef
    stance: ArgumentStance
    text: str
    claims: tuple[ClaimStatement, ...] = ()
    evidence_ids: tuple[EvidencePackId, ...] = ()
    unsupported: bool = False
    invocation_id: InvocationId | None = None


@dataclass(frozen=True, slots=True)
class RevisePositionRequest:
    run_id: RunId
    position_id: PositionId
    stance: ArgumentStance
    reason: RevisionReason


@dataclass(frozen=True, slots=True)
class RecordAbstentionRequest:
    run_id: RunId
    stakeholder_id: StakeholderId
    topic: TopicRef


@dataclass(frozen=True, slots=True)
class TrackConflictTopicRequest:
    run_id: RunId
    topic: TopicRef
    stances: Mapping[StakeholderId, ArgumentStance]


@dataclass(frozen=True, slots=True)
class FormCoalitionRequest:
    run_id: RunId
    topic: TopicRef
    member_ids: tuple[StakeholderId, ...]
    proposal: Proposal
    conditions: Mapping[StakeholderId, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CloseRoundRequest:
    run_id: RunId
    learning: RoundLearning
    convergence: str = "unmeasured"


@dataclass(frozen=True, slots=True)
class GetSimulationRunRequest:
    run_id: RunId


@dataclass(frozen=True, slots=True)
class ListRoundsRequest:
    run_id: RunId
    cursor: str | None = None
    limit: int = 50


@dataclass(frozen=True, slots=True)
class ListConflictTopicsRequest:
    run_id: RunId
    status: ConflictStatus | None = None


@dataclass(frozen=True, slots=True)
class ListRoundLearningRequest:
    run_id: RunId


@dataclass(frozen=True, slots=True)
class ReplaySimulationHistoryRequest:
    run_id: RunId
    until_round: int | None = None


@dataclass(frozen=True, slots=True)
class SummariseIntermediateResultRequest:
    run_id: RunId
    round_number: int | None = None
