"""Domain services of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Service classification)

These are stateless rules over run state: stopping conditions (Strategy + Specification),
contradiction detection and turn-order policy. They never load or save; the aggregate calls them
inside its transaction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from negotiation_session.domain.entities import Argument
from negotiation_session.domain.values import (
    ArgumentContradiction,
    ArgumentStance,
    ConsensusLevel,
    StakeholderBinding,
    StakeholderId,
    StoppingCondition,
    TopicRef,
    TurnAssignment,
)


class EvaluateStoppingCondition:
    """Pure specification evaluation: consensus, round cap then deadlock (first match wins)."""

    def evaluate(
        self,
        *,
        consensus: ConsensusLevel,
        rounds_done: int,
        round_cap: int,
        deadlocked: bool,
    ) -> StoppingCondition:
        raise NotImplementedError("EvaluateStoppingCondition.evaluate is implemented by issue #292")


class DetectArgumentContradiction:
    """Compare claims and stances inside and across arguments of one topic."""

    _OPPOSING = frozenset(
        {
            frozenset({ArgumentStance.SUPPORT, ArgumentStance.OPPOSE}),
            frozenset({ArgumentStance.CONDITIONAL_ACCEPT, ArgumentStance.OPPOSE}),
        }
    )

    def detect(self, arguments: Sequence[Argument]) -> Sequence[ArgumentContradiction]:
        findings: list[ArgumentContradiction] = []
        ordered = list(arguments)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                if self.contradicts(left, right):
                    findings.append(self._finding(left, right))
        return findings

    def contradicts(self, left: Argument, right: Argument) -> bool:
        if left.id == right.id or left.stakeholder == right.stakeholder:
            return False
        if left.target.topic != right.target.topic:
            return False
        return frozenset({left.stance, right.stance}) in self._OPPOSING

    def _finding(self, left: Argument, right: Argument) -> ArgumentContradiction:
        return ArgumentContradiction(
            argument_id_a=left.id,
            argument_id_b=right.id,
            topic=left.target.topic,
            stance_a=left.stance,
            stance_b=right.stance,
        )


@runtime_checkable
class TurnOrderPolicy(Protocol):
    """Strategy for allocating one round's speaking order."""

    def assign(
        self,
        *,
        bound: Mapping[StakeholderId, StakeholderBinding],
        round_number: int,
        topics: Sequence[TopicRef],
    ) -> tuple[TurnAssignment, ...]: ...


def _topic_for(topics: Sequence[TopicRef]) -> TopicRef:
    return topics[0] if topics else TopicRef("general")


def _assignments(
    stakeholders: Sequence[StakeholderId], topic: TopicRef
) -> tuple[TurnAssignment, ...]:
    return tuple(
        TurnAssignment(stakeholder=stakeholder, topic=topic, order=index)
        for index, stakeholder in enumerate(stakeholders)
    )


class RoundRobinTurnOrder:
    """Deterministic, evenly distributed speaking order (stable across replays)."""

    def assign(
        self,
        *,
        bound: Mapping[StakeholderId, StakeholderBinding],
        round_number: int,
        topics: Sequence[TopicRef],
    ) -> tuple[TurnAssignment, ...]:
        topic = _topic_for(topics)
        ordered = sorted(bound, key=lambda stakeholder: (round_number, stakeholder))
        return _assignments(ordered, topic)


class PowerWeightedTurnOrder:
    """Weight the order by derived negotiating power; recorded for audit."""

    def assign(
        self,
        *,
        bound: Mapping[StakeholderId, StakeholderBinding],
        round_number: int,
        topics: Sequence[TopicRef],
    ) -> tuple[TurnAssignment, ...]:
        topic = _topic_for(topics)

        def weight(stakeholder: StakeholderId) -> tuple[int, int, str]:
            binding = bound[stakeholder]
            return (-len(binding.veto_classes), -len(binding.interests), stakeholder)

        return _assignments(sorted(bound, key=weight), topic)


class AffectedFirstTurnOrder:
    """Actors whose mandate covers the topic speak before the others."""

    def assign(
        self,
        *,
        bound: Mapping[StakeholderId, StakeholderBinding],
        round_number: int,
        topics: Sequence[TopicRef],
    ) -> tuple[TurnAssignment, ...]:
        topic = _topic_for(topics)
        affected = {
            stakeholder for stakeholder, binding in bound.items() if topic in binding.mandate_topics
        }

        def rank(stakeholder: StakeholderId) -> tuple[int, str]:
            return (0 if stakeholder in affected else 1, stakeholder)

        return _assignments(sorted(bound, key=rank), topic)
