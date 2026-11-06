"""Owned entities of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Owned entities and value objects)

These entities live inside the ``SimulationRun`` aggregate and are only mutated through it.
Every mutating method raises ``NotImplementedError`` naming the implementing issue; its
signature and return type are frozen.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field

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
        raise NotImplementedError("Position.initial is implemented by issue #289")

    def supersede(
        self,
        *,
        new_id: PositionId,
        stance: ArgumentStance,
        reason: RevisionReason,
    ) -> Position:
        raise NotImplementedError("Position.supersede is implemented by issue #289")

    @property
    def is_open(self) -> bool:
        raise NotImplementedError("Position.is_open is implemented by issue #289")


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
        raise NotImplementedError("Argument.new is implemented by issue #290")

    @property
    def is_evidenced(self) -> bool:
        raise NotImplementedError("Argument.is_evidenced is implemented by issue #290")


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
        raise NotImplementedError("NegotiationRound.open is implemented by issue #287")

    def assert_turn_available(self, stakeholder: StakeholderId, topic: TopicRef) -> None:
        raise NotImplementedError(
            "NegotiationRound.assert_turn_available is implemented by issue #291"
        )

    def record_position(self, position: Position) -> Position:
        raise NotImplementedError("NegotiationRound.record_position is implemented by issue #289")

    def record_argument(self, argument: Argument) -> Argument:
        raise NotImplementedError("NegotiationRound.record_argument is implemented by issue #291")

    def record_abstention(self, stakeholder: StakeholderId, topic: TopicRef) -> None:
        raise NotImplementedError("NegotiationRound.record_abstention is implemented by issue #287")

    def assert_everyone_accounted_for(self, bound: Collection[StakeholderId]) -> None:
        raise NotImplementedError(
            "NegotiationRound.assert_everyone_accounted_for is implemented by issue #287"
        )

    def attach_learning(self, learning: RoundLearning) -> None:
        raise NotImplementedError("NegotiationRound.attach_learning is implemented by issue #294")

    def close(self) -> None:
        raise NotImplementedError("NegotiationRound.close is implemented by issue #287")

    def carry_learning(self) -> RoundLearning | None:
        raise NotImplementedError("NegotiationRound.carry_learning is implemented by issue #294")

    def open_position_for(self, stakeholder: StakeholderId, topic: TopicRef) -> Position | None:
        raise NotImplementedError("NegotiationRound.open_position_for is implemented by issue #289")

    @property
    def is_closed(self) -> bool:
        raise NotImplementedError("NegotiationRound.is_closed is implemented by issue #287")

    @property
    def turn_outcomes(self) -> Sequence[TurnOutcome]:
        raise NotImplementedError("NegotiationRound.turn_outcomes is implemented by issue #291")
