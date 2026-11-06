"""Frozen application services of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Service classification, API)

Constructors, service names and ``execute`` signatures are frozen. Bodies raise
``NotImplementedError`` naming the implementing issue; later issues may not rename or remove a
frozen member without a new freeze entry. Business rules stay in the aggregate.
"""

from __future__ import annotations

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
from negotiation_session.domain.repositories import RunEventLog, SimulationRunRepository


class TranslateQuestionToMandate:
    """Moderator policy: turn a policy question into a bounded, immutable mandate."""

    def __init__(self, *, clock: Clock, ids: IdFactory) -> None:
        self._clock = clock
        self._ids = ids

    async def execute(self, request: TranslateQuestionToMandateRequest) -> MandateResult:
        raise NotImplementedError("TranslateQuestionToMandate.execute is implemented by issue #285")


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
        raise NotImplementedError("GetSimulationRun.execute is implemented by issue #283")


class ListRounds:
    """Project round summaries and their learning."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListRoundsRequest) -> Sequence[RoundSummaryResult]:
        raise NotImplementedError("ListRounds.execute is implemented by issue #294")


class ListConflictTopics:
    """Project tracked conflicts, optionally filtered by status."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListConflictTopicsRequest) -> Sequence[ConflictTopicResult]:
        raise NotImplementedError("ListConflictTopics.execute is implemented by issue #284")


class ListRoundLearning:
    """Project per-round learning insight sets."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListRoundLearningRequest) -> Sequence[RoundLearningResult]:
        raise NotImplementedError("ListRoundLearning.execute is implemented by issue #294")


class SummariseIntermediateResult:
    """Project round state for the moderator; never mutates the run."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(
        self, request: SummariseIntermediateResultRequest
    ) -> IntermediateSummaryResult:
        raise NotImplementedError(
            "SummariseIntermediateResult.execute is implemented by issue #285"
        )


class ReplaySimulationHistory:
    """Fold the append-only run log to round N and return the reconstructed state (AC 11)."""

    def __init__(self, *, runs: SimulationRunRepository, event_log: RunEventLog) -> None:
        self._runs = runs
        self._event_log = event_log

    async def execute(self, request: ReplaySimulationHistoryRequest) -> ReplayResult:
        raise NotImplementedError("ReplaySimulationHistory.execute is implemented by issue #296")


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
