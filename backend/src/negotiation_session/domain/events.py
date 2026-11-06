"""Frozen domain-event payloads of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Domain Events)

Event names are past-tense immutable facts. Payloads carry ids plus the minimum a consumer
needs; consumers re-read the run for detail. Every event is published through the outbox in the
same transaction that saved the aggregate (ADR-002/ADR-003). ``LoggedEvent`` is the append-only
run-log record with the per-run ordinal that replay folds (AC 11, W9).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from negotiation_session.domain.values import (
    ArgumentId,
    ArgumentStance,
    CoalitionId,
    EvidencePackId,
    InvocationId,
    NegotiationPhase,
    PositionId,
    Proposal,
    RunId,
    StakeholderId,
    StoppingConditionName,
    TargetRef,
    TopicRef,
)


@dataclass(frozen=True, slots=True)
class SimulationRunOpened:
    """A run was created from a mandate with a pinned corpus snapshot and bound stakeholders."""

    name: ClassVar[str] = "SimulationRunOpened"
    run_id: RunId
    mandate_hash: str
    snapshot_id: str
    stakeholder_ids: tuple[StakeholderId, ...]


@dataclass(frozen=True, slots=True)
class RoundOpened:
    """A round started with its turn order and the learning carried into it."""

    name: ClassVar[str] = "RoundOpened"
    run_id: RunId
    round: int
    turn_order: tuple[StakeholderId, ...]
    phase: NegotiationPhase


@dataclass(frozen=True, slots=True)
class InitialPositionStated:
    """A stakeholder opened its evidenced starting position."""

    name: ClassVar[str] = "InitialPositionStated"
    run_id: RunId
    round: int
    stakeholder_id: StakeholderId
    topic: TopicRef
    position_id: PositionId
    stance: ArgumentStance
    evidence_ids: tuple[EvidencePackId, ...]


@dataclass(frozen=True, slots=True)
class ArgumentSubmitted:
    """A stakeholder contributed an argument with stance, claims and citations."""

    name: ClassVar[str] = "ArgumentSubmitted"
    run_id: RunId
    round: int
    argument_id: ArgumentId
    stakeholder_id: StakeholderId
    target: TargetRef
    stance: ArgumentStance
    evidence_ids: tuple[EvidencePackId, ...]
    invocation_id: InvocationId


@dataclass(frozen=True, slots=True)
class PositionRevised:
    """A position changed with a recorded reason citing its cause."""

    name: ClassVar[str] = "PositionRevised"
    run_id: RunId
    round: int
    stakeholder_id: StakeholderId
    topic: TopicRef
    position_id: PositionId
    from_stance: ArgumentStance
    to_stance: ArgumentStance
    argument_ids: tuple[ArgumentId, ...]
    pack_ids: tuple[EvidencePackId, ...]


@dataclass(frozen=True, slots=True)
class PositionRevisionRejected:
    """A change was refused for lack of causal reason; no state changed."""

    name: ClassVar[str] = "PositionRevisionRejected"
    run_id: RunId
    stakeholder_id: StakeholderId
    topic: TopicRef
    reason_code: str


@dataclass(frozen=True, slots=True)
class ConflictTopicOpened:
    """Divergence was formalised as a tracked conflict with its stance map."""

    name: ClassVar[str] = "ConflictTopicOpened"
    run_id: RunId
    round: int
    topic: TopicRef
    stances: Mapping[StakeholderId, ArgumentStance]


@dataclass(frozen=True, slots=True)
class CoalitionOffered:
    """An institution invited another to join a shared proposal, with conditions."""

    name: ClassVar[str] = "CoalitionOffered"
    run_id: RunId
    round: int
    coalition_id: CoalitionId
    invited_id: StakeholderId
    conditions: str


@dataclass(frozen=True, slots=True)
class CoalitionOfferDeclined:
    """An invited institution refused the shared proposal, with reason."""

    name: ClassVar[str] = "CoalitionOfferDeclined"
    run_id: RunId
    round: int
    coalition_id: CoalitionId
    stakeholder_id: StakeholderId
    reason: str


@dataclass(frozen=True, slots=True)
class CoalitionFormed:
    """Stakeholders aligned behind one explicit shared proposal."""

    name: ClassVar[str] = "CoalitionFormed"
    run_id: RunId
    round: int
    topic: TopicRef
    coalition_id: CoalitionId
    members: tuple[StakeholderId, ...]
    proposal: Proposal


@dataclass(frozen=True, slots=True)
class AbstentionRecorded:
    """A stakeholder's floor was resolved as an abstention, not a silent skip."""

    name: ClassVar[str] = "AbstentionRecorded"
    run_id: RunId
    round: int
    stakeholder_id: StakeholderId
    topic: TopicRef


@dataclass(frozen=True, slots=True)
class RoundLearningCaptured:
    """A round's outcomes were distilled for the next round's prompt."""

    name: ClassVar[str] = "RoundLearningCaptured"
    run_id: RunId
    round: int
    insight_count: int
    insight_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoundClosed:
    """All turns completed; convergence measured and the learning attached."""

    name: ClassVar[str] = "RoundClosed"
    run_id: RunId
    round: int
    convergence: str
    evidence_count: int


@dataclass(frozen=True, slots=True)
class LearningApplied:
    """A stakeholder explicitly applied a captured insight to a later turn."""

    name: ClassVar[str] = "LearningApplied"
    run_id: RunId
    stakeholder_id: StakeholderId
    insight_type: str
    learning_round: int
    argument_id: ArgumentId


@dataclass(frozen=True, slots=True)
class NegotiationPhaseAdvanced:
    """The run entered the next phase; the admissible command set changed."""

    name: ClassVar[str] = "NegotiationPhaseAdvanced"
    run_id: RunId
    round: int
    from_phase: NegotiationPhase
    to_phase: NegotiationPhase


@dataclass(frozen=True, slots=True)
class SimulationRunClosed:
    """The run terminated because a stopping condition fired."""

    name: ClassVar[str] = "SimulationRunClosed"
    run_id: RunId
    condition: StoppingConditionName
    rounds: int
    final_phase: NegotiationPhase


type DomainEvent = (
    SimulationRunOpened
    | RoundOpened
    | InitialPositionStated
    | ArgumentSubmitted
    | PositionRevised
    | PositionRevisionRejected
    | ConflictTopicOpened
    | CoalitionOffered
    | CoalitionOfferDeclined
    | CoalitionFormed
    | AbstentionRecorded
    | RoundLearningCaptured
    | RoundClosed
    | LearningApplied
    | NegotiationPhaseAdvanced
    | SimulationRunClosed
)


@dataclass(frozen=True, slots=True)
class LoggedEvent:
    """One append-only run-log record; ``sequence`` is the per-run ordinal (W9)."""

    sequence: int
    event: DomainEvent
    occurred_at: datetime | None = None


type EventBatch = Sequence[LoggedEvent]
