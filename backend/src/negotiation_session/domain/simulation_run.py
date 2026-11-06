"""The ``SimulationRun`` aggregate root (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Aggregate root — SimulationRun)

The run is the consistency boundary: every guard below is enforced inside one aggregate
transaction, and every state change appends to ``events``. Components whose issue has not landed
yet raise ``NotImplementedError`` naming that issue.
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
from negotiation_session.domain.errors import (
    ArgumentWithoutEvidence,
    ClosedRunImmutable,
    NegotiationRoundNotFound,
    PhaseRegression,
    PositionNotFound,
    RevisionWithoutCause,
    RoundCapExceeded,
    RoundStillOpen,
    StakeholderNotBound,
)
from negotiation_session.domain.events import (
    AbstentionRecorded,
    ArgumentSubmitted,
    ConflictTopicOpened,
    DomainEvent,
    InitialPositionStated,
    NegotiationPhaseAdvanced,
    PositionRevised,
    PositionRevisionRejected,
    RoundClosed,
    RoundLearningCaptured,
    RoundOpened,
    SimulationRunOpened,
)
from negotiation_session.domain.values import (
    ArgumentId,
    ArgumentStance,
    ClaimEvidence,
    ClaimStatement,
    CoalitionId,
    ConflictTopicId,
    ConsensusLevel,
    EvidencePackId,
    InvocationId,
    NegotiationPhase,
    PositionId,
    Proposal,
    RevisionReason,
    RoundId,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingCondition,
    TargetRef,
    TopicRef,
    TurnAssignment,
)
from shared.ids import new_id


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
        if mandate.round_cap < 1:
            raise ValueError("round_cap must be at least 1")
        if not bound:
            raise ValueError("a run requires at least one bound stakeholder")
        mandate.phase = NegotiationPhase.POSITION_FORMATION
        run = cls(
            id=run_id,
            mandate=mandate,
            phase=NegotiationPhase.POSITION_FORMATION,
            round_cap=mandate.round_cap,
            bound=dict(bound),
        )
        run.events.append(
            SimulationRunOpened(
                run_id=run_id,
                mandate_hash=mandate.mandate_hash,
                snapshot_id="",
                stakeholder_ids=tuple(sorted(bound)),
            )
        )
        return run

    @property
    def is_closed(self) -> bool:
        return self.phase is NegotiationPhase.CLOSED

    @property
    def current_round(self) -> NegotiationRound:
        if not self.rounds:
            raise NegotiationRoundNotFound(f"run {self.id} has no open round")
        return self.rounds[-1]

    def open_round(self) -> NegotiationRound:
        self._assert_mutable()
        if self.rounds and not self.rounds[-1].is_closed:
            raise RoundStillOpen(f"round {self.rounds[-1].number} is still open in run {self.id}")
        if len(self.rounds) >= self.round_cap:
            raise RoundCapExceeded(f"run {self.id} reached its round cap of {self.round_cap}")
        carried = self.rounds[-1].carry_learning() if self.rounds else None
        round_ = NegotiationRound.open(
            round_id=RoundId(new_id("rnd")),
            number=len(self.rounds) + 1,
            turn_order=self.turn_order(),
            learning=carried,
        )
        self.rounds.append(round_)
        self.events.append(
            RoundOpened(
                run_id=self.id,
                round=round_.number,
                turn_order=tuple(assignment.stakeholder for assignment in round_.turn_order),
                phase=self.phase,
            )
        )
        if len(self.rounds) > 1 and self.phase is NegotiationPhase.POSITION_FORMATION:
            self.advance_phase(NegotiationPhase.DEBATE)
        return round_

    def submit_initial_position(
        self,
        stakeholder: StakeholderId,
        topic: TopicRef,
        stance: ArgumentStance,
        proposal: Proposal,
        evidence: Sequence[ClaimEvidence],
    ) -> Position:
        self._assert_mutable()
        self._assert_bound(stakeholder)
        if self.phase is not NegotiationPhase.POSITION_FORMATION:
            raise PhaseRegression(
                f"initial positions are only admissible in position formation, not {self.phase}"
            )
        if not evidence:
            raise ArgumentWithoutEvidence(f"position of {stakeholder} on {topic} cites no evidence")
        round_ = self.current_round
        position = Position.initial(
            position_id=PositionId(new_id("pos")),
            stakeholder=stakeholder,
            topic=topic,
            stance=stance,
            proposal=proposal,
            evidence=evidence,
            round_number=round_.number,
        )
        recorded = round_.record_position(position)
        self.events.append(
            InitialPositionStated(
                run_id=self.id,
                round=round_.number,
                stakeholder_id=stakeholder,
                topic=topic,
                stance=stance,
                evidence_ids=tuple(item.evidence_id for item in recorded.evidence),
            )
        )
        return recorded

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
        self._assert_mutable()
        self._assert_bound(stakeholder)
        round_ = self.current_round
        round_.assert_turn_available(stakeholder, target.topic)
        if not evidence and not unsupported:
            raise ArgumentWithoutEvidence(
                f"argument of {stakeholder} cites no evidence and is not flagged unsupported"
            )
        argument = Argument.new(
            argument_id=ArgumentId(new_id("arg")),
            stakeholder=stakeholder,
            target=target,
            stance=stance,
            text=text,
            claims=claims,
            evidence=evidence,
            unsupported=unsupported,
            round_number=round_.number,
            invocation_id=invocation_id,
        )
        round_.record_argument(argument)
        self.events.append(
            ArgumentSubmitted(
                run_id=self.id,
                round=round_.number,
                argument_id=argument.id,
                stakeholder_id=stakeholder,
                target=target,
                stance=stance,
                evidence_ids=tuple(item.evidence_id for item in argument.evidence),
                invocation_id=invocation_id or InvocationId(""),
            )
        )
        return argument

    def revise_position(
        self,
        stakeholder: StakeholderId,
        topic: TopicRef,
        stance: ArgumentStance,
        reason: RevisionReason,
    ) -> Position:
        self._assert_mutable()
        self._assert_bound(stakeholder)
        round_ = self.current_round
        position = round_.require_open_position(stakeholder, topic)
        if not reason.cites(argument_ids=self._argument_ids(), pack_ids=self._evidence_ids()):
            self.events.append(
                PositionRevisionRejected(
                    run_id=self.id,
                    stakeholder_id=stakeholder,
                    topic=topic,
                    reason_code=RevisionWithoutCause.code,
                )
            )
            raise RevisionWithoutCause(
                f"revision of {stakeholder} on {topic} cites no argument and no evidence pack"
            )
        revised = position.supersede(new_id=PositionId(new_id("pos")), stance=stance, reason=reason)
        round_.record_position(revised)
        self.events.append(
            PositionRevised(
                run_id=self.id,
                stakeholder_id=stakeholder,
                topic=topic,
                position_id=revised.id,
                from_stance=position.stance,
                to_stance=revised.stance,
                argument_ids=reason.argument_ids,
                pack_ids=reason.pack_ids,
            )
        )
        return revised

    def record_abstention(self, stakeholder: StakeholderId, topic: TopicRef) -> None:
        self._assert_mutable()
        self._assert_bound(stakeholder)
        round_ = self.current_round
        round_.record_abstention(stakeholder, topic)
        self.events.append(
            AbstentionRecorded(
                run_id=self.id,
                round=round_.number,
                stakeholder_id=stakeholder,
                topic=topic,
            )
        )

    def track_conflict(
        self, topic: TopicRef, stances: Mapping[StakeholderId, ArgumentStance]
    ) -> ConflictTopic:
        self._assert_mutable()
        conflict = ConflictTopic.open(
            conflict_id=ConflictTopicId(new_id("cft")), topic=topic, stances=stances
        )
        self.conflicts[topic] = conflict
        self.events.append(ConflictTopicOpened(run_id=self.id, topic=topic, stances=dict(stances)))
        return conflict

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
        self._assert_mutable()
        round_ = self.current_round
        round_.assert_everyone_accounted_for(self.bound)
        round_.attach_learning(learning)
        round_.close()
        self.events.append(
            RoundLearningCaptured(
                run_id=self.id,
                round=round_.number,
                insight_count=len(learning.insights),
                insight_types=tuple(item.insight_type.value for item in learning.insights),
            )
        )
        self.events.append(
            RoundClosed(
                run_id=self.id,
                round=round_.number,
                convergence="unmeasured",
                evidence_count=sum(len(argument.evidence) for argument in round_.arguments),
            )
        )

    def evaluate_stopping(self, consensus: ConsensusLevel) -> StoppingCondition:
        raise NotImplementedError("SimulationRun.evaluate_stopping is implemented by issue #292")

    def advance_phase(self, target: NegotiationPhase) -> None:
        if self.phase is target:
            return
        if self.is_closed:
            raise ClosedRunImmutable(f"run {self.id} is closed")
        if not self.phase.can_advance_to(target):
            raise PhaseRegression(f"cannot move phase from {self.phase} to {target}")
        previous = self.phase
        self.phase = target
        self.mandate.phase = target
        self.events.append(
            NegotiationPhaseAdvanced(run_id=self.id, from_phase=previous, to_phase=target)
        )

    def turn_order(self) -> tuple[TurnAssignment, ...]:
        topic = TopicRef(self.mandate.question)
        return tuple(
            TurnAssignment(stakeholder=stakeholder, topic=topic, order=index)
            for index, stakeholder in enumerate(sorted(self.bound))
        )

    def drain_events(self) -> list[DomainEvent]:
        drained = self.events
        self.events = []
        return drained

    def open_position(self, stakeholder: StakeholderId, topic: TopicRef) -> Position:
        return self.current_round.require_open_position(stakeholder, topic)

    def position_by_id(self, position_id: PositionId) -> Position:
        for round_ in self.rounds:
            for position in round_.positions.values():
                if position.id == position_id:
                    return position
        raise PositionNotFound(f"no position {position_id} in run {self.id}")

    def _assert_mutable(self) -> None:
        if self.is_closed:
            raise ClosedRunImmutable(f"run {self.id} is closed and immutable")

    def _assert_bound(self, stakeholder: StakeholderId) -> None:
        if stakeholder not in self.bound:
            raise StakeholderNotBound(f"stakeholder {stakeholder} is not bound to run {self.id}")

    def _argument_ids(self) -> tuple[ArgumentId, ...]:
        return tuple(argument.id for round_ in self.rounds for argument in round_.arguments)

    def _evidence_ids(self) -> tuple[EvidencePackId, ...]:
        ids: list[EvidencePackId] = []
        for round_ in self.rounds:
            for position in round_.positions.values():
                ids.extend(item.evidence_id for item in position.evidence)
            for argument in round_.arguments:
                ids.extend(item.evidence_id for item in argument.evidence)
        return tuple(ids)
