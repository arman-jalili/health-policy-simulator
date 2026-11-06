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

    def detect(self, arguments: Sequence[Argument]) -> Sequence[ArgumentContradiction]:
        raise NotImplementedError("DetectArgumentContradiction.detect is implemented by issue #284")

    def contradicts(self, left: Argument, right: Argument) -> bool:
        raise NotImplementedError(
            "DetectArgumentContradiction.contradicts is implemented by issue #284"
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
