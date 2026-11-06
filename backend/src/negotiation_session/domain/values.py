"""Frozen value vocabulary of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md``

Value objects are immutable and equal by value. ``NegotiationPhase`` is the monotonic state
label; ``StoppingCondition`` is the named terminal rule with its parameters. Rule-bearing
methods raise ``NotImplementedError`` naming the implementing issue — their signatures are
frozen now and may not change without a new freeze entry.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import NewType

RunId = NewType("RunId", str)
MandateId = NewType("MandateId", str)
RoundId = NewType("RoundId", str)
PositionId = NewType("PositionId", str)
ArgumentId = NewType("ArgumentId", str)
ConflictTopicId = NewType("ConflictTopicId", str)
CoalitionId = NewType("CoalitionId", str)
CoalitionOfferId = NewType("CoalitionOfferId", str)
LearningId = NewType("LearningId", str)
StakeholderId = NewType("StakeholderId", str)
TopicRef = NewType("TopicRef", str)
EvidencePackId = NewType("EvidencePackId", str)
InvocationId = NewType("InvocationId", str)


class NegotiationPhase(StrEnum):
    """Monotonic stage of a run. Order is declared in the enumeration below."""

    DRAFT = "draft"
    POSITION_FORMATION = "position_formation"
    DEBATE = "debate"
    NEGOTIATION = "negotiation"
    COMPROMISE = "compromise"
    CLOSED = "closed"

    @property
    def rank(self) -> int:
        return _PHASE_RANK[self]

    @property
    def is_terminal(self) -> bool:
        return self is NegotiationPhase.CLOSED

    def can_advance_to(self, target: NegotiationPhase) -> bool:
        """Return whether moving to ``target`` is monotonic (forward-only, no regression)."""
        return self is not target and _PHASE_RANK[target] > _PHASE_RANK[self]


_PHASE_RANK: dict[NegotiationPhase, int] = {
    phase: index for index, phase in enumerate(NegotiationPhase)
}


class ArgumentStance(StrEnum):
    """A stakeholder's stance on a conflict topic, in a position or an argument."""

    SUPPORT = "support"
    OPPOSE = "oppose"
    QUALIFY = "qualify"
    CONDITIONAL_ACCEPT = "conditional_accept"


class ProposalQuantification(StrEnum):
    """A proposal component is quantified or explicitly unquantified (invariant 10)."""

    QUANTIFIED = "quantified"
    UNQUANTIFIED = "unquantified"


class LearningInsightType(StrEnum):
    """Classification of a round lesson; consumed by the next round's prompt."""

    SHARED_INTEREST = "shared_interest"
    BLOCKING_CONSTRAINT = "blocking_constraint"
    EVIDENCE_GAP = "evidence_gap"
    COALITION_SIGNAL = "coalition_signal"
    POSITION_SHIFT = "position_shift"


class StoppingConditionName(StrEnum):
    """Named terminal rules evaluated as specifications (Strategy pattern)."""

    CONSENSUS = "consensus"
    ROUND_CAP = "round_cap"
    DEADLOCK = "deadlock"


class ConsensusLevel(StrEnum):
    """Moderator-supplied convergence measure used by the consensus condition."""

    NONE = "none"
    EMERGING = "emerging"
    SUFFICIENT = "sufficient"


class ConflictStatus(StrEnum):
    """Lifecycle of a formalised point of disagreement."""

    OPEN = "open"
    RESOLVED = "resolved"
    DEADLOCKED = "deadlocked"


class CoalitionOfferStatus(StrEnum):
    """Invitation lifecycle: offered → accepted | declined."""

    OFFERED = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class TurnOutcome(StrEnum):
    """What a stakeholder did with its floor in a round."""

    PENDING = "pending"
    SPOKE = "spoke"
    ABSTAINED = "abstained"


@dataclass(frozen=True, slots=True)
class ProvenanceRef:
    """Vector-free citation carried into the domain through the ACL."""

    source_id: str
    source_uri: str
    outlet: str
    published_on: date | None = None


@dataclass(frozen=True, slots=True)
class ClaimEvidence:
    """An evidence reference cited by a position or argument.

    It is the ACL target of ``EvidencePackView``: passage id, stance and provenance — never a
    retrieval hit, score or embedding vector.
    """

    evidence_id: EvidencePackId
    passage_id: str
    stance: str
    provenance: ProvenanceRef | None = None


@dataclass(frozen=True, slots=True)
class ClaimStatement:
    """A claim inside an argument, gated by a ClaimValidation verdict before acceptance."""

    text: str
    claim_id: str | None = None
    verdict: str | None = None


@dataclass(frozen=True, slots=True)
class TargetRef:
    """What an argument is addressed to: a topic, optionally a position or argument."""

    topic: TopicRef
    position_id: PositionId | None = None
    argument_id: ArgumentId | None = None


@dataclass(frozen=True, slots=True)
class StakeholderBinding:
    """Partner view of a bound institution as the domain sees it.

    ACL target of ``StakeholderProfileView`` (StakeholderModel). Keeping the domain value local
    preserves the dependency-direction guard: ``domain/`` imports no other context's layers.
    """

    stakeholder_id: StakeholderId
    institution_name: str
    institution_code: str
    interests: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    red_lines: tuple[str, ...] = ()
    veto_classes: tuple[str, ...] = ()
    mandate_topics: tuple[TopicRef, ...] = ()
    profile_version: str = ""
    persona_version: str = ""
    allowed_evidence_tiers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProposalComponent:
    """One admissible part of a proposal with its own support record."""

    measure: str
    effect: str
    population: str
    cost_eur: Decimal | None = None
    quantification: ProposalQuantification = ProposalQuantification.QUANTIFIED
    support_record: tuple[EvidencePackId, ...] = ()

    def is_admissible_for_impact(self) -> bool:
        raise NotImplementedError(
            "ProposalComponent.is_admissible_for_impact is implemented by issue #284"
        )


@dataclass(frozen=True, slots=True)
class Proposal:
    """Structured measure bundle; comparable across agents (Composite over components)."""

    summary: str
    components: tuple[ProposalComponent, ...] = ()

    def quantified_components(self) -> tuple[ProposalComponent, ...]:
        raise NotImplementedError("Proposal.quantified_components is implemented by issue #284")

    def is_fully_quantified(self) -> bool:
        raise NotImplementedError("Proposal.is_fully_quantified is implemented by issue #284")


@dataclass(frozen=True, slots=True)
class RevisionReason:
    """Structured justification citing arguments and evidence that caused a change."""

    argument_ids: tuple[ArgumentId, ...] = ()
    pack_ids: tuple[EvidencePackId, ...] = ()
    driver: str = ""

    def cites(
        self,
        *,
        argument_ids: Collection[ArgumentId],
        pack_ids: Collection[EvidencePackId],
    ) -> bool:
        """Return whether the reason cites at least one argument or evidence pack."""
        return bool(set(self.argument_ids) & set(argument_ids)) or bool(
            set(self.pack_ids) & set(pack_ids)
        )


@dataclass(frozen=True, slots=True)
class TurnAssignment:
    """A stakeholder's floor in a round: order, topic and outcome."""

    stakeholder: StakeholderId
    topic: TopicRef
    order: int
    outcome: TurnOutcome = TurnOutcome.PENDING


@dataclass(frozen=True, slots=True)
class LearningInsight:
    """One distilled lesson; it derives only from this run's arguments (invariant 14)."""

    insight_type: LearningInsightType
    statement: str
    derived_from: tuple[ArgumentId, ...] = ()
    round_number: int = 0


@dataclass(frozen=True, slots=True)
class LearningApplication:
    """Explicit link from a later turn to the round learning it applies (invariant 13)."""

    learning_id: LearningId
    learning_round: int
    insight_type: LearningInsightType
    argument_id: ArgumentId


@dataclass(frozen=True, slots=True)
class StoppingCondition:
    """A named terminal rule with its parameters and firing outcome."""

    name: StoppingConditionName
    fired: bool
    parameters: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def evaluate(
        cls,
        *,
        consensus: ConsensusLevel,
        rounds_done: int,
        round_cap: int,
        deadlocked: bool,
    ) -> StoppingCondition:
        raise NotImplementedError("StoppingCondition.evaluate is implemented by issue #292")


@dataclass(frozen=True, slots=True)
class ArgumentContradiction:
    """Two arguments of one topic whose stances cannot both hold."""

    argument_id_a: ArgumentId
    argument_id_b: ArgumentId
    topic: TopicRef
    stance_a: ArgumentStance
    stance_b: ArgumentStance
