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


class RoundRobinTurnOrder:
    """Deterministic, evenly distributed speaking order."""

    def assign(
        self,
        *,
        bound: Mapping[StakeholderId, StakeholderBinding],
        round_number: int,
        topics: Sequence[TopicRef],
    ) -> tuple[TurnAssignment, ...]:
        raise NotImplementedError("RoundRobinTurnOrder.assign is implemented by issue #291")


class PowerWeightedTurnOrder:
    """Weight the order by derived negotiating power; recorded for audit."""

    def assign(
        self,
        *,
        bound: Mapping[StakeholderId, StakeholderBinding],
        round_number: int,
        topics: Sequence[TopicRef],
    ) -> tuple[TurnAssignment, ...]:
        raise NotImplementedError("PowerWeightedTurnOrder.assign is implemented by issue #291")


class AffectedFirstTurnOrder:
    """Actors most affected by the topic speak before the others."""

    def assign(
        self,
        *,
        bound: Mapping[StakeholderId, StakeholderBinding],
        round_number: int,
        topics: Sequence[TopicRef],
    ) -> tuple[TurnAssignment, ...]:
        raise NotImplementedError("AffectedFirstTurnOrder.assign is implemented by issue #291")
