"""Frozen application services of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Service classification, API)

Constructors, service names and ``execute`` signatures are frozen. Bodies raise
``NotImplementedError`` naming the implementing issue; later issues may not rename or remove a
frozen member without a new freeze entry. Business rules stay in the aggregate.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from negotiation_session.application.commands import (
    CloseRoundRequest,
    FormCoalitionRequest,
    GetSimulationRunRequest,
    ListConflictTopicsRequest,
    ListRoundLearningRequest,
    ListRoundsRequest,
    OpenSimulationRunRequest,
    RecordAbstentionRequest,
    ReplaySimulationHistoryRequest,
    RevisePositionRequest,
    SelectRelevantStakeholdersRequest,
    SubmitInitialPositionRequest,
    SummariseIntermediateResultRequest,
    TakeNegotiationTurnRequest,
    TrackConflictTopicRequest,
    TranslateQuestionToMandateRequest,
)
from negotiation_session.application.dto import (
    ArgumentResult,
    CloseRoundResult,
    CoalitionResult,
    ConflictTopicResult,
    IntermediateSummaryResult,
    LearningInsightResult,
    MandateResult,
    OpenSimulationRunResult,
    PositionResult,
    ReplayResult,
    RoundLearningResult,
    RoundSummaryResult,
    SimulationRunResult,
    StakeholderSelectionResult,
)
from negotiation_session.application.ports import (
    ClaimVerdictGate,
    Clock,
    EventPublisher,
    EvidencePackReader,
    GovernanceGuard,
    IdFactory,
    InvocationLookup,
    StakeholderDirectory,
    UnitOfWork,
)
from negotiation_session.domain.entities import (
    ConflictTopic,
    NegotiationMandate,
    NegotiationRound,
    RoundLearning,
)
from negotiation_session.domain.errors import SimulationRunNotFound
from negotiation_session.domain.repositories import RunEventLog, SimulationRunRepository
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ConflictStatus,
    MandateId,
    RunId,
    StoppingConditionName,
)


class TranslateQuestionToMandate:
    """Moderator policy: turn a policy question into a bounded, immutable mandate."""

    def __init__(self, *, clock: Clock, ids: IdFactory) -> None:
        self._clock = clock
        self._ids = ids

    async def execute(self, request: TranslateQuestionToMandateRequest) -> MandateResult:
        conditions = request.stopping_conditions or (
            StoppingConditionName.CONSENSUS,
            StoppingConditionName.ROUND_CAP,
            StoppingConditionName.DEADLOCK,
        )
        mandate = NegotiationMandate(
            id=MandateId(self._ids.new_id("mnd")),
            question=request.question,
            objective=request.question,
            constraints=request.constraints,
            round_cap=request.round_cap,
            stopping_conditions=conditions,
            profile_version="v1",
            mandate_hash=hashlib.sha256(
                f"{request.question}|{request.round_cap}".encode()
            ).hexdigest(),
        )
        return _mandate_result(mandate)


class SelectRelevantStakeholders:
    """Delegate selection to StakeholderModel and record the rationale."""

    def __init__(self, *, stakeholders: StakeholderDirectory) -> None:
        self._stakeholders = stakeholders

    async def execute(
        self, request: SelectRelevantStakeholdersRequest
    ) -> StakeholderSelectionResult:
        raise NotImplementedError("SelectRelevantStakeholders.execute is implemented by issue #285")


class OpenSimulationRun:
    """Transaction boundary: create the aggregate, bind stakeholders, write the outbox."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        stakeholders: StakeholderDirectory,
        clock: Clock,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._stakeholders = stakeholders
        self._clock = clock
        self._ids = ids
        self._uow = uow

    async def execute(self, request: OpenSimulationRunRequest) -> OpenSimulationRunResult:
        raise NotImplementedError("OpenSimulationRun.execute is implemented by issue #283")


class SubmitInitialPosition:
    """Load-mutate-save one evidenced starting position."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        evidence: EvidencePackReader,
        guard: GovernanceGuard,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._evidence = evidence
        self._guard = guard
        self._ids = ids
        self._uow = uow

    async def execute(self, request: SubmitInitialPositionRequest) -> PositionResult:
        raise NotImplementedError("SubmitInitialPosition.execute is implemented by issue #289")


class TakeNegotiationTurn:
    """Load-mutate-save one argued turn; claims are gated by verdicts."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        evidence: EvidencePackReader,
        claims: ClaimVerdictGate,
        guard: GovernanceGuard,
        invocations: InvocationLookup,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._evidence = evidence
        self._claims = claims
        self._guard = guard
        self._invocations = invocations
        self._ids = ids
        self._uow = uow

    async def execute(self, request: TakeNegotiationTurnRequest) -> ArgumentResult:
        raise NotImplementedError("TakeNegotiationTurn.execute is implemented by issue #290")


class RevisePosition:
    """Load-mutate-save a position revision with a causal reason."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        evidence: EvidencePackReader,
        guard: GovernanceGuard,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._evidence = evidence
        self._guard = guard
        self._ids = ids
        self._uow = uow

    async def execute(self, request: RevisePositionRequest) -> PositionResult:
        raise NotImplementedError("RevisePosition.execute is implemented by issue #288")


class RecordAbstention:
    """Record the absence of a turn so the round-close guard is truthful."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._ids = ids
        self._uow = uow

    async def execute(self, request: RecordAbstentionRequest) -> SimulationRunResult:
        raise NotImplementedError("RecordAbstention.execute is implemented by issue #287")


class TrackConflictTopic:
    """Formalise a divergence as a tracked conflict with its stance map."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._ids = ids
        self._uow = uow

    async def execute(self, request: TrackConflictTopicRequest) -> ConflictTopicResult:
        raise NotImplementedError("TrackConflictTopic.execute is implemented by issue #284")


class FormCoalition:
    """Orchestrate offers and membership inside the run; no retroactive support."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._ids = ids
        self._uow = uow

    async def execute(self, request: FormCoalitionRequest) -> CoalitionResult:
        raise NotImplementedError("FormCoalition.execute is implemented by issue #293")


class CloseRound:
    """Close the current round with its learning, then evaluate the stopping condition."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._ids = ids
        self._uow = uow

    async def execute(self, request: CloseRoundRequest) -> CloseRoundResult:
        raise NotImplementedError("CloseRound.execute is implemented by issue #287")


class GetSimulationRun:
    """Read the run's current state without mutating it."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: GetSimulationRunRequest) -> SimulationRunResult:
        return _run_result(await _require_run(self._runs, request.run_id))


class ListRounds:
    """Project round summaries and their learning."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListRoundsRequest) -> Sequence[RoundSummaryResult]:
        run = await _require_run(self._runs, request.run_id)
        rounds = run.rounds[: max(request.limit, 0)]
        return tuple(_round_result(run.id, round_) for round_ in rounds)


class ListConflictTopics:
    """Project tracked conflicts, optionally filtered by status."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListConflictTopicsRequest) -> Sequence[ConflictTopicResult]:
        run = await _require_run(self._runs, request.run_id)
        return tuple(
            _conflict_result(run.id, conflict)
            for conflict in run.conflicts.values()
            if request.status is None or conflict.status is request.status
        )


class ListRoundLearning:
    """Project per-round learning insight sets."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListRoundLearningRequest) -> Sequence[RoundLearningResult]:
        run = await _require_run(self._runs, request.run_id)
        return tuple(
            _learning_result(run.id, round_.number, round_.learning)
            for round_ in run.rounds
            if round_.learning is not None
        )


class SummariseIntermediateResult:
    """Project round state for the moderator; never mutates the run."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(
        self, request: SummariseIntermediateResultRequest
    ) -> IntermediateSummaryResult:
        run = await _require_run(self._runs, request.run_id)
        current = request.round_number or (run.rounds[-1].number if run.rounds else 0)
        return IntermediateSummaryResult(
            run_id=run.id,
            round=current,
            phase=run.phase,
            consensus="unmeasured",
            open_conflicts=tuple(
                topic
                for topic, conflict in run.conflicts.items()
                if conflict.status is ConflictStatus.OPEN
            ),
            coalition_ids=tuple(run.coalitions),
            argument_count=sum(len(round_.arguments) for round_ in run.rounds),
        )


class ReplaySimulationHistory:
    """Fold the append-only run log to round N and return the reconstructed state (AC 11)."""

    def __init__(self, *, runs: SimulationRunRepository, event_log: RunEventLog) -> None:
        self._runs = runs
        self._event_log = event_log

    async def execute(self, request: ReplaySimulationHistoryRequest) -> ReplayResult:
        raise NotImplementedError("ReplaySimulationHistory.execute is implemented by issue #296")


# ── Projection helpers ──────────────────────────────────────────────────────


async def _require_run(runs: SimulationRunRepository, run_id: RunId) -> SimulationRun:
    run = await runs.get(run_id)
    if run is None:
        raise SimulationRunNotFound(f"no simulation run {run_id}")
    return run


def _mandate_result(mandate: NegotiationMandate) -> MandateResult:
    return MandateResult(
        mandate_id=str(mandate.id),
        question=mandate.question,
        objective=mandate.objective,
        constraints=mandate.constraints,
        round_cap=mandate.round_cap,
        stopping_conditions=mandate.stopping_conditions,
        mandate_hash=mandate.mandate_hash,
    )


def _run_result(run: SimulationRun) -> SimulationRunResult:
    return SimulationRunResult(
        run_id=run.id,
        phase=run.phase,
        round=run.rounds[-1].number if run.rounds else 0,
        round_cap=run.round_cap,
        closed=run.is_closed,
        bound_stakeholder_ids=tuple(run.bound),
        open_position_ids=tuple(
            position.id
            for round_ in run.rounds
            for position in round_.positions.values()
            if position.is_open
        ),
        coalition_ids=tuple(run.coalitions),
    )


def _round_result(run_id: RunId, round_: NegotiationRound) -> RoundSummaryResult:
    return RoundSummaryResult(
        round=round_.number,
        closed=round_.is_closed,
        argument_count=len(round_.arguments),
        abstention_count=len(round_.abstentions),
        learning=(
            _learning_result(run_id, round_.number, round_.learning)
            if round_.learning is not None
            else None
        ),
    )


def _learning_result(
    run_id: RunId, round_number: int, learning: RoundLearning | None
) -> RoundLearningResult:
    if learning is None:
        raise ValueError(f"round {round_number} has no learning record")
    return RoundLearningResult(
        learning_id=learning.id,
        run_id=run_id,
        round=round_number,
        insights=tuple(
            LearningInsightResult(
                insight_type=insight.insight_type.value,
                statement=insight.statement,
                derived_from=insight.derived_from,
                round_number=insight.round_number,
            )
            for insight in learning.insights
        ),
    )


def _conflict_result(run_id: RunId, conflict: ConflictTopic) -> ConflictTopicResult:
    return ConflictTopicResult(
        conflict_id=conflict.id,
        run_id=run_id,
        topic=conflict.topic,
        status=conflict.status,
        stances=dict(conflict.stances),
    )


# ── Frozen service classification (ADR-008) ─────────────────────────────────
# Application services load-mutate-save the aggregate or project read models; domain services
# are pure rule evaluation. A name may not move between layers without a new freeze entry.
SERVICE_CLASSIFICATION: Mapping[str, str] = {
    "TranslateQuestionToMandate": "application",
    "SelectRelevantStakeholders": "application",
    "OpenSimulationRun": "application",
    "SubmitInitialPosition": "application",
    "TakeNegotiationTurn": "application",
    "RevisePosition": "application",
    "RecordAbstention": "application",
    "TrackConflictTopic": "application",
    "FormCoalition": "application",
    "CloseRound": "application",
    "GetSimulationRun": "application",
    "ListRounds": "application",
    "ListConflictTopics": "application",
    "ListRoundLearning": "application",
    "SummariseIntermediateResult": "application",
    "ReplaySimulationHistory": "application",
    "EvaluateStoppingCondition": "domain",
    "DetectArgumentContradiction": "domain",
    "TurnOrderPolicy": "domain",
}
