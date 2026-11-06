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
    OpenRound,
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
from negotiation_session.domain.repositories import RunEventLog, SimulationRunRepository
from negotiation_session.domain.values import RunId
from negotiation_session.infrastructure.acl import PositionProvenanceAcl
from negotiation_session.infrastructure.progress import InMemoryProgressBroker
from negotiation_session.infrastructure.repository.memory import (
    InMemoryRunEventLog,
    InMemorySimulationRunRepository,
)
from negotiation_session.infrastructure.repository.sqlalchemy import (
    SqlAlchemyRunEventLog,
    SqlAlchemySimulationRunRepository,
)
from shared.config import Settings
from shared.db import Database
from shared.db import UnitOfWork as DbUnitOfWork
from shared.enums import Environment, Persistence
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
    open_round: OpenRound
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

    def subscribe_run_closed(self, handler: object) -> None:
        """Register the ConsensusAnalysis run-closed subscriber (issue #406)."""
        self.close_round.subscribe_run_closed(handler)  # type: ignore[arg-type]
        self.open_round.subscribe_run_closed(handler)  # type: ignore[arg-type]

    def bind_position_provenance(self, provenance: object) -> UnitOfWork:
        """Bind the disclosure producer after the GovernanceCompliance container exists."""
        self.close_round._provenance = provenance  # type: ignore[assignment]
        return self.close_round._uow

    def readiness(self) -> tuple[str, str]:
        """Return ``(state, adapter)`` for the persistence family actually bound."""
        adapter = type(self.open_simulation_run._runs).__name__
        return ("ok", adapter)


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

    PostgreSQL uses the aggregate snapshot and append-only event log from migrations 0401/0402;
    memory remains the explicit test/local family.
    """
    if settings.persistence is Persistence.MEMORY and settings.env is not Environment.LOCAL:
        raise ValueError("PERSISTENCE=memory is only allowed with ENV=local")
    if settings.persistence is Persistence.POSTGRES:
        runs: SimulationRunRepository = SqlAlchemySimulationRunRepository(database.session_factory)
        event_log: RunEventLog = SqlAlchemyRunEventLog(database.session_factory)
        active_uow: UnitOfWork = DbUnitOfWork(database.session_factory)
    else:
        runs = InMemorySimulationRunRepository()
        event_log = InMemoryRunEventLog()
        active_uow = _NullUnitOfWork()
    broker: RunProgressStream = progress or InMemoryProgressBroker()
    publisher = _ProgressEventPublisher(broker)
    ids: IdFactory = UuidFactory()

    return NegotiationSessionContainer(
        translate_question_to_mandate=TranslateQuestionToMandate(ids=ids),
        select_relevant_stakeholders=SelectRelevantStakeholders(stakeholders=stakeholders),
        open_simulation_run=OpenSimulationRun(
            runs=runs,
            event_log=event_log,
            events=publisher,
            stakeholders=stakeholders,
            ids=ids,
            uow=active_uow,
        ),
        open_round=OpenRound(runs=runs, event_log=event_log, events=publisher, uow=active_uow),
        submit_initial_position=SubmitInitialPosition(
            runs=runs,
            event_log=event_log,
            events=publisher,
            evidence=evidence,
            guard=governance,
            uow=active_uow,
        ),
        take_negotiation_turn=TakeNegotiationTurn(
            runs=runs,
            event_log=event_log,
            events=publisher,
            evidence=evidence,
            claims=claims,
            guard=governance,
            invocations=invocations,
            uow=active_uow,
        ),
        revise_position=RevisePosition(
            runs=runs,
            event_log=event_log,
            events=publisher,
            guard=governance,
            uow=active_uow,
        ),
        record_abstention=RecordAbstention(
            runs=runs, event_log=event_log, events=publisher, uow=active_uow
        ),
        track_conflict_topic=TrackConflictTopic(
            runs=runs, event_log=event_log, events=publisher, uow=active_uow
        ),
        form_coalition=FormCoalition(
            runs=runs, event_log=event_log, events=publisher, ids=ids, uow=active_uow
        ),
        close_round=CloseRound(
            runs=runs,
            event_log=event_log,
            events=publisher,
            provenance=PositionProvenanceAcl(),
            uow=active_uow,
        ),
        get_simulation_run=GetSimulationRun(runs=runs),
        list_rounds=ListRounds(runs=runs),
        list_conflict_topics=ListConflictTopics(runs=runs),
        list_round_learning=ListRoundLearning(runs=runs),
        summarise_intermediate_result=SummariseIntermediateResult(runs=runs),
        replay_simulation_history=ReplaySimulationHistory(runs=runs, event_log=event_log),
        progress_stream=broker,
    )
