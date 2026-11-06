"""Frozen composition factory of NegotiationSession (contract frozen, issue #282).

Wired by issue #299: the container builds the use cases over the configured adapters, binds every
ACL port and exposes the progress stream the SSE route reads. ``shared/app.py`` mounts the router
and stores the container on ``app.state.negotiation_session``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from negotiation_session.application.ports import (
    ClaimVerdictGate,
    Clock,
    EvidencePackReader,
    GovernanceGuard,
    IdFactory,
    InvocationLookup,
    RunProgressPublisher,
    RunProgressStream,
    StakeholderDirectory,
    UnitOfWork,
)
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
    SelectRelevantStakeholders,
    SubmitInitialPosition,
    SummariseIntermediateResult,
    TakeNegotiationTurn,
    TrackConflictTopic,
    TranslateQuestionToMandate,
)
from negotiation_session.domain.events import DomainEvent
from negotiation_session.domain.values import RunId
from negotiation_session.infrastructure.progress import InMemoryProgressBroker
from negotiation_session.infrastructure.repository.memory import (
    InMemoryRunEventLog,
    InMemorySimulationRunRepository,
)
from shared.config import Settings
from shared.db import Database
from shared.ids import new_id


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class UuidFactory:
    def new_id(self, prefix: str) -> str:
        return new_id(prefix)


class _NullUnitOfWork:
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[object]:
        yield None


class _ProgressEventPublisher:
    """Forward drained domain events to the SSE broker, grouped by run."""

    def __init__(self, progress: RunProgressStream) -> None:
        self._progress = progress

    async def publish(self, events: Sequence[DomainEvent], *, trace_id: str | None = None) -> None:
        if not events or not hasattr(self._progress, "publish"):
            return
        publisher = cast(RunProgressPublisher, self._progress)
        grouped: dict[str, list[DomainEvent]] = {}
        for event in events:
            grouped.setdefault(str(event.run_id), []).append(event)
        for run_id, batch in grouped.items():
            await publisher.publish(RunId(run_id), batch)


@dataclass(frozen=True, slots=True)
class NegotiationSessionContainer:
    translate_question_to_mandate: TranslateQuestionToMandate
    select_relevant_stakeholders: SelectRelevantStakeholders
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
    progress_stream: RunProgressStream


def build_container(
    settings: Settings,
    database: Database,
    *,
    evidence: EvidencePackReader,
    stakeholders: StakeholderDirectory,
    claims: ClaimVerdictGate,
    governance: GovernanceGuard,
    invocations: InvocationLookup,
    progress: RunProgressStream,
) -> NegotiationSessionContainer:
    """Build every use case over the injected ports.

    Persistence: negotiation state uses the in-memory aggregate/log adapters for both configured
    families; the SQLAlchemy family is tracked in the module runbook (deferred migration 0401).
    """
    del settings, database  # configuration is validated by the app shell
    runs = InMemorySimulationRunRepository()
    event_log = InMemoryRunEventLog()
    broker: RunProgressStream = progress or InMemoryProgressBroker()
    publisher = _ProgressEventPublisher(broker)
    clock: Clock = SystemClock()
    ids: IdFactory = UuidFactory()
    uow: UnitOfWork = _NullUnitOfWork()

    return NegotiationSessionContainer(
        translate_question_to_mandate=TranslateQuestionToMandate(clock=clock, ids=ids),
        select_relevant_stakeholders=SelectRelevantStakeholders(stakeholders=stakeholders),
        open_simulation_run=OpenSimulationRun(
            runs=runs,
            event_log=event_log,
            events=publisher,
            stakeholders=stakeholders,
            clock=clock,
            ids=ids,
            uow=uow,
        ),
        submit_initial_position=SubmitInitialPosition(
            runs=runs,
            event_log=event_log,
            events=publisher,
            evidence=evidence,
            guard=governance,
            ids=ids,
            uow=uow,
        ),
        take_negotiation_turn=TakeNegotiationTurn(
            runs=runs,
            event_log=event_log,
            events=publisher,
            evidence=evidence,
            claims=claims,
            guard=governance,
            invocations=invocations,
            ids=ids,
            uow=uow,
        ),
        revise_position=RevisePosition(
            runs=runs,
            event_log=event_log,
            events=publisher,
            evidence=evidence,
            guard=governance,
            ids=ids,
            uow=uow,
        ),
        record_abstention=RecordAbstention(
            runs=runs, event_log=event_log, events=publisher, ids=ids, uow=uow
        ),
        track_conflict_topic=TrackConflictTopic(
            runs=runs, event_log=event_log, events=publisher, ids=ids, uow=uow
        ),
        form_coalition=FormCoalition(
            runs=runs, event_log=event_log, events=publisher, ids=ids, uow=uow
        ),
        close_round=CloseRound(runs=runs, event_log=event_log, events=publisher, ids=ids, uow=uow),
        get_simulation_run=GetSimulationRun(runs=runs),
        list_rounds=ListRounds(runs=runs),
        list_conflict_topics=ListConflictTopics(runs=runs),
        list_round_learning=ListRoundLearning(runs=runs),
        summarise_intermediate_result=SummariseIntermediateResult(runs=runs),
        replay_simulation_history=ReplaySimulationHistory(runs=runs, event_log=event_log),
        progress_stream=broker,
    )
