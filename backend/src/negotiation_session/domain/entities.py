"""Owned entities of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Owned entities and value objects)

These entities live inside the ``SimulationRun`` aggregate and are only mutated through it.
Methods whose component is not implemented yet raise ``NotImplementedError`` naming the
implementing issue; their signatures and return types are frozen.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace

from negotiation_session.domain.errors import (
    DuplicateTurn,
    PositionNotFound,
    RoundCloseGuardViolation,
    RoundLearningMissing,
    TurnNotAvailable,
)
from negotiation_session.domain.values import (
    ArgumentId,
    ArgumentStance,
    ClaimEvidence,
    ClaimStatement,
    CoalitionId,
    CoalitionOfferId,
    CoalitionOfferStatus,
    ConflictStatus,
    ConflictTopicId,
    InvocationId,
    LearningId,
    LearningInsight,
    MandateId,
    NegotiationPhase,
    PositionId,
    Proposal,
    RevisionReason,
    RoundId,
    StakeholderId,
    StoppingConditionName,
    TargetRef,
    TopicRef,
    TurnAssignment,
    TurnOutcome,
)


@dataclass(slots=True)
class NegotiationMandate:
    """Moderator framing: objective, constraints, rules, actor set and stopping conditions."""

    id: MandateId
    question: str
    objective: str
    constraints: tuple[str, ...]
    round_cap: int
    stopping_conditions: tuple[StoppingConditionName, ...]
    profile_version: str
    phase: NegotiationPhase = NegotiationPhase.DRAFT
    mandate_hash: str = ""

    def is_immutable_after_open(self) -> bool:
        raise NotImplementedError(
            "NegotiationMandate.is_immutable_after_open is implemented by issue #284"
        )


@dataclass(slots=True)
class Position:
    """A stakeholder's evidenced stance on a topic, with lineage; superseded, never duplicated.

    ``superseded_by`` marks a closed lineage entry; ``supersedes`` points back. At most one
    position per (stakeholder, topic) is open at any time (AC 4).
    """

    id: PositionId
    stakeholder: StakeholderId
    topic: TopicRef
    stance: ArgumentStance
    proposal: Proposal
    evidence: tuple[ClaimEvidence, ...]
    round_number: int
    revision: RevisionReason | None = None
    supersedes: PositionId | None = None
    superseded_by: PositionId | None = None

    @classmethod
    def initial(
        cls,
        *,
        position_id: PositionId,
        stakeholder: StakeholderId,
        topic: TopicRef,
        stance: ArgumentStance,
        proposal: Proposal,
        evidence: Sequence[ClaimEvidence],
        round_number: int,
    ) -> Position:
        return cls(
            id=position_id,
            stakeholder=stakeholder,
            topic=topic,
            stance=stance,
            proposal=proposal,
            evidence=tuple(evidence),
            round_number=round_number,
        )

    def supersede(
        self,
        *,
        new_id: PositionId,
        stance: ArgumentStance,
        reason: RevisionReason,
    ) -> Position:
        """Close this lineage entry and return its successor with the new stance."""
        self.superseded_by = new_id
        return type(self)(
            id=new_id,
            stakeholder=self.stakeholder,
            topic=self.topic,
            stance=stance,
            proposal=self.proposal,
            evidence=self.evidence,
            round_number=self.round_number,
            revision=reason,
            supersedes=self.id,
        )

    @property
    def is_open(self) -> bool:
        return self.superseded_by is None


@dataclass(slots=True)
class Argument:
    """One turn's reasoned contribution: stance, claims and citations; immutable once submitted."""

    id: ArgumentId
    stakeholder: StakeholderId
    target: TargetRef
    stance: ArgumentStance
    text: str
    claims: tuple[ClaimStatement, ...]
    evidence: tuple[ClaimEvidence, ...]
    unsupported: bool
    round_number: int
    invocation_id: InvocationId | None = None

    @classmethod
    def new(
        cls,
        *,
        argument_id: ArgumentId,
        stakeholder: StakeholderId,
        target: TargetRef,
        stance: ArgumentStance,
        text: str,
        claims: Sequence[ClaimStatement],
        evidence: Sequence[ClaimEvidence],
        unsupported: bool,
        round_number: int,
        invocation_id: InvocationId | None = None,
    ) -> Argument:
        return cls(
            id=argument_id,
            stakeholder=stakeholder,
            target=target,
            stance=stance,
            text=text,
            claims=tuple(claims),
            evidence=tuple(evidence),
            unsupported=unsupported,
            round_number=round_number,
            invocation_id=invocation_id,
        )

    @property
    def is_evidenced(self) -> bool:
        return bool(self.evidence) or self.unsupported


@dataclass(slots=True)
class ConflictTopic:
    """A formalised point of disagreement tracked across rounds with its stance history."""

    id: ConflictTopicId
    topic: TopicRef
    status: ConflictStatus
    stances: dict[StakeholderId, ArgumentStance] = field(default_factory=dict)
    history: list[tuple[int, StakeholderId, ArgumentStance]] = field(default_factory=list)

    @classmethod
    def open(
        cls,
        *,
        conflict_id: ConflictTopicId,
        topic: TopicRef,
        stances: Mapping[StakeholderId, ArgumentStance],
    ) -> ConflictTopic:
        raise NotImplementedError("ConflictTopic.open is implemented by issue #284")

    def record_stance(
        self, stakeholder: StakeholderId, stance: ArgumentStance, round_number: int
    ) -> None:
        raise NotImplementedError("ConflictTopic.record_stance is implemented by issue #284")


@dataclass(slots=True)
class CoalitionOffer:
    """Recorded invitation with conditions and an offered → accepted | declined lifecycle."""

    id: CoalitionOfferId
    coalition_id: CoalitionId
    invited: StakeholderId
    conditions: str
    status: CoalitionOfferStatus = CoalitionOfferStatus.OFFERED
    decline_reason: str | None = None

    @classmethod
    def offer(
        cls,
        *,
        offer_id: CoalitionOfferId,
        coalition_id: CoalitionId,
        invited: StakeholderId,
        conditions: str,
    ) -> CoalitionOffer:
        raise NotImplementedError("CoalitionOffer.offer is implemented by issue #293")

    def accept(self) -> None:
        raise NotImplementedError("CoalitionOffer.accept is implemented by issue #293")

    def decline(self, reason: str) -> None:
        raise NotImplementedError("CoalitionOffer.decline is implemented by issue #293")


@dataclass(slots=True)
class Coalition:
    """Stakeholders aligned behind one explicit shared proposal; membership requires an offer."""

    id: CoalitionId
    topic: TopicRef
    proposal: Proposal
    members: list[StakeholderId] = field(default_factory=list)
    offers: dict[StakeholderId, CoalitionOffer] = field(default_factory=dict)

    @classmethod
    def form(
        cls,
        *,
        coalition_id: CoalitionId,
        topic: TopicRef,
        proposal: Proposal,
        offers: Mapping[StakeholderId, CoalitionOffer],
    ) -> Coalition:
        raise NotImplementedError("Coalition.form is implemented by issue #293")

    def add_member(self, stakeholder: StakeholderId) -> None:
        raise NotImplementedError("Coalition.add_member is implemented by issue #293")


@dataclass(slots=True)
class RoundLearning:
    """Persisted digest of a round's outcomes, consumed by the next round's prompt."""

    id: LearningId
    round_number: int
    insights: tuple[LearningInsight, ...] = ()

    @classmethod
    def capture(
        cls,
        *,
        learning_id: LearningId,
        round_number: int,
        insights: Sequence[LearningInsight],
    ) -> RoundLearning:
        raise NotImplementedError("RoundLearning.capture is implemented by issue #294")

    def to_prompt_payload(self) -> Mapping[str, object]:
        raise NotImplementedError("RoundLearning.to_prompt_payload is implemented by issue #294")


@dataclass(slots=True)
class NegotiationRound:
    """A numbered turn cycle closed by the moderator with a learning record."""

    id: RoundId
    number: int
    turn_order: list[TurnAssignment] = field(default_factory=list)
    positions: dict[tuple[StakeholderId, TopicRef], Position] = field(default_factory=dict)
    arguments: list[Argument] = field(default_factory=list)
    abstentions: dict[StakeholderId, TopicRef] = field(default_factory=dict)
    learning: RoundLearning | None = None
    closed: bool = False

    @classmethod
    def open(
        cls,
        *,
        round_id: RoundId,
        number: int,
        turn_order: Sequence[TurnAssignment],
        learning: RoundLearning | None = None,
    ) -> NegotiationRound:
        return cls(
            id=round_id,
            number=number,
            turn_order=list(turn_order),
            learning=learning,
        )

    def assert_turn_available(self, stakeholder: StakeholderId, topic: TopicRef) -> None:
        if any(
            argument.stakeholder == stakeholder and argument.target.topic == topic
            for argument in self.arguments
        ):
            raise DuplicateTurn(
                f"stakeholder {stakeholder} already took a turn on {topic} in round {self.number}"
            )
        if self.abstentions.get(stakeholder) == topic:
            raise DuplicateTurn(
                f"stakeholder {stakeholder} abstained on {topic} in round {self.number}"
            )
        if self.turn_order and not any(
            assignment.stakeholder == stakeholder for assignment in self.turn_order
        ):
            raise TurnNotAvailable(f"stakeholder {stakeholder} has no floor in round {self.number}")

    def record_position(self, position: Position) -> Position:
        key = (position.stakeholder, position.topic)
        existing = self.positions.get(key)
        if existing is not None and existing.is_open and existing.id != position.id:
            existing.superseded_by = position.id
            if position.supersedes is None:
                position.supersedes = existing.id
        self.positions[key] = position
        return position

    def record_argument(self, argument: Argument) -> Argument:
        self.arguments.append(argument)
        self._mark_outcome(argument.stakeholder, TurnOutcome.SPOKE)
        return argument

    def record_abstention(self, stakeholder: StakeholderId, topic: TopicRef) -> None:
        self.abstentions[stakeholder] = topic
        self._mark_outcome(stakeholder, TurnOutcome.ABSTAINED)

    def _mark_outcome(self, stakeholder: StakeholderId, outcome: TurnOutcome) -> None:
        for index, assignment in enumerate(self.turn_order):
            if assignment.stakeholder == stakeholder:
                self.turn_order[index] = replace(assignment, outcome=outcome)
                break

    def assert_everyone_accounted_for(self, bound: Collection[StakeholderId]) -> None:
        missing = [stakeholder for stakeholder in bound if not self._is_accounted_for(stakeholder)]
        if missing:
            raise RoundCloseGuardViolation(
                f"round {self.number} cannot close; unaccounted: {', '.join(sorted(missing))}"
            )

    def _is_accounted_for(self, stakeholder: StakeholderId) -> bool:
        if stakeholder in self.abstentions:
            return True
        if any(argument.stakeholder == stakeholder for argument in self.arguments):
            return True
        return any(
            position.stakeholder == stakeholder and position.is_open
            for position in self.positions.values()
        )

    def attach_learning(self, learning: RoundLearning) -> None:
        if learning is None:
            raise RoundLearningMissing(f"round {self.number} has no learning record")
        self.learning = learning

    def close(self) -> None:
        if self.learning is None:
            raise RoundLearningMissing(f"round {self.number} has no learning record")
        self.closed = True

    def carry_learning(self) -> RoundLearning | None:
        return self.learning

    def open_position_for(self, stakeholder: StakeholderId, topic: TopicRef) -> Position | None:
        position = self.positions.get((stakeholder, topic))
        if position is None or not position.is_open:
            return None
        return position

    def require_open_position(self, stakeholder: StakeholderId, topic: TopicRef) -> Position:
        position = self.open_position_for(stakeholder, topic)
        if position is None:
            raise PositionNotFound(f"no open position for {stakeholder} on {topic}")
        return position

    @property
    def is_closed(self) -> bool:
        return self.closed

    @property
    def turn_outcomes(self) -> Sequence[TurnOutcome]:
        return tuple(assignment.outcome for assignment in self.turn_order)
