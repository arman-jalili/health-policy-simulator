"""The ``SimulationRun`` aggregate root (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Aggregate root — SimulationRun)

The run is the consistency boundary: every guard below is enforced inside one aggregate
transaction, and every state change appends to ``events``. Bodies raise ``NotImplementedError``
naming the implementing issue; signatures are frozen.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from negotiation_session.domain.entities import (
    Argument,
    Coalition,
    ConflictTopic,
    NegotiationMandate,
    NegotiationRound,
    Position,
    RoundLearning,
)
from negotiation_session.domain.events import DomainEvent
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    ClaimStatement,
    CoalitionId,
    ConsensusLevel,
    InvocationId,
    NegotiationPhase,
    PositionId,
    Proposal,
    RevisionReason,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingCondition,
    TargetRef,
    TopicRef,
    TurnAssignment,
)


@dataclass(slots=True)
class SimulationRun:
    """One end-to-end negotiation over one policy question."""

    id: RunId
    mandate: NegotiationMandate
    phase: NegotiationPhase
    round_cap: int
    bound: Mapping[StakeholderId, StakeholderBinding]
    rounds: list[NegotiationRound] = field(default_factory=list)
    conflicts: dict[TopicRef, ConflictTopic] = field(default_factory=dict)
    coalitions: dict[CoalitionId, Coalition] = field(default_factory=dict)
    events: list[DomainEvent] = field(default_factory=list)

    @classmethod
    def open(
        cls,
        *,
        run_id: RunId,
        mandate: NegotiationMandate,
        bound: Mapping[StakeholderId, StakeholderBinding],
    ) -> SimulationRun:
        raise NotImplementedError("SimulationRun.open is implemented by issue #283")

    @property
    def is_closed(self) -> bool:
        raise NotImplementedError("SimulationRun.is_closed is implemented by issue #283")

    @property
    def current_round(self) -> NegotiationRound:
        raise NotImplementedError("SimulationRun.current_round is implemented by issue #283")

    def open_round(self) -> NegotiationRound:
        raise NotImplementedError("SimulationRun.open_round is implemented by issue #286")

    def submit_initial_position(
        self,
        stakeholder: StakeholderId,
        topic: TopicRef,
        stance: ArgumentStance,
        proposal: Proposal,
        evidence: Sequence[ClaimEvidence],
    ) -> Position:
        raise NotImplementedError(
            "SimulationRun.submit_initial_position is implemented by issue #289"
        )

    def take_turn(
        self,
        stakeholder: StakeholderId,
        target: TargetRef,
        stance: ArgumentStance,
        text: str,
        claims: Sequence[ClaimStatement],
        evidence: Sequence[ClaimEvidence],
        *,
        unsupported: bool = False,
        invocation_id: InvocationId | None = None,
    ) -> Argument:
        raise NotImplementedError("SimulationRun.take_turn is implemented by issue #290")

    def revise_position(
        self,
        stakeholder: StakeholderId,
        topic: TopicRef,
        stance: ArgumentStance,
        reason: RevisionReason,
    ) -> Position:
        raise NotImplementedError("SimulationRun.revise_position is implemented by issue #288")

    def record_abstention(self, stakeholder: StakeholderId, topic: TopicRef) -> None:
        raise NotImplementedError("SimulationRun.record_abstention is implemented by issue #287")

    def track_conflict(
        self, topic: TopicRef, stances: Mapping[StakeholderId, ArgumentStance]
    ) -> ConflictTopic:
        raise NotImplementedError("SimulationRun.track_conflict is implemented by issue #284")

    def form_coalition(
        self,
        *,
        topic: TopicRef,
        member_ids: Sequence[StakeholderId],
        proposal: Proposal,
        coalition_id: CoalitionId,
    ) -> Coalition:
        raise NotImplementedError("SimulationRun.form_coalition is implemented by issue #293")

    def close_round(self, learning: RoundLearning) -> None:
        raise NotImplementedError("SimulationRun.close_round is implemented by issue #287")

    def evaluate_stopping(self, consensus: ConsensusLevel) -> StoppingCondition:
        raise NotImplementedError("SimulationRun.evaluate_stopping is implemented by issue #292")

    def advance_phase(self, target: NegotiationPhase) -> None:
        raise NotImplementedError("SimulationRun.advance_phase is implemented by issue #286")

    def turn_order(self) -> tuple[TurnAssignment, ...]:
        raise NotImplementedError("SimulationRun.turn_order is implemented by issue #291")

    def drain_events(self) -> list[DomainEvent]:
        raise NotImplementedError("SimulationRun.drain_events is implemented by issue #283")

    def open_position(self, stakeholder: StakeholderId, topic: TopicRef) -> Position:
        raise NotImplementedError("SimulationRun.open_position is implemented by issue #289")

    def position_by_id(self, position_id: PositionId) -> Position:
        raise NotImplementedError("SimulationRun.position_by_id is implemented by issue #288")
