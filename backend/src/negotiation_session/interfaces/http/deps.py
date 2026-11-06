"""HTTP container dependency (contract frozen, issue #282)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from negotiation_session.application.services import (
    CloseRound,
    FormCoalition,
    GetSimulationRun,
    ListConflictTopics,
    ListRoundLearning,
    ListRounds,
    OpenSimulationRun,
    RecordAbstention,
    ReplaySimulationHistory,
    RevisePosition,
    SubmitInitialPosition,
    SummariseIntermediateResult,
    TakeNegotiationTurn,
    TrackConflictTopic,
    TranslateQuestionToMandate,
)


class NegotiationSessionContainer(Protocol):
    translate_question_to_mandate: TranslateQuestionToMandate
    open_simulation_run: OpenSimulationRun
    submit_initial_position: SubmitInitialPosition
    take_negotiation_turn: TakeNegotiationTurn
    revise_position: RevisePosition
    record_abstention: RecordAbstention
    track_conflict_topic: TrackConflictTopic
    form_coalition: FormCoalition
    close_round: CloseRound
    get_simulation_run: GetSimulationRun
    list_rounds: ListRounds
    list_conflict_topics: ListConflictTopics
    list_round_learning: ListRoundLearning
    summarise_intermediate_result: SummariseIntermediateResult
    replay_simulation_history: ReplaySimulationHistory


@dataclass(frozen=True, slots=True)
class ContainerView:
    container: NegotiationSessionContainer


def get_container(request: Request) -> NegotiationSessionContainer:
    container = getattr(request.app.state, "negotiation_session", None)
    if container is None:
        raise RuntimeError("negotiation_session container is not mounted")
    return container  # type: ignore[no-any-return]
