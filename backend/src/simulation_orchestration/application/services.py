"""Frozen application services of SimulationOrchestration (issue #205).

Canonical: .pi/architecture/modules/simulation-orchestration.md

Constructors, service names and ``execute`` signatures are frozen. Bodies raise
``NotImplementedError`` naming the issue that implements them; later issues may not rename or
remove a frozen member without a new freeze entry.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from simulation_orchestration.application.commands import (
    CollectUsageReportRequest,
    GetJobRequest,
    PauseOrResumeSimulationRequest,
    RecordAgentInvocationRequest,
    RegisterPromptTemplateRequest,
    ResolvePromptTemplateRequest,
    StartSimulationRequest,
    StreamSimulationProgressRequest,
)
from simulation_orchestration.application.dto import (
    InvocationRecordResult,
    JobSnapshotResult,
    PauseResumeResult,
    ProgressEventView,
    PromptTemplateResult,
    StartSimulationResult,
    UsageReportResult,
)
from simulation_orchestration.application.ports import (
    Clock,
    NegotiationGateway,
    PriceTable,
    UnitOfWork,
    WorkflowGraph,
)
from simulation_orchestration.application.repositories import (
    InvocationStore,
    JobStore,
    ProgressStore,
    PromptRegistry,
)
from simulation_orchestration.application.rules import (
    BudgetGuard,
    CheckpointPolicy,
    PromptVersioning,
)


class RunSimulationJob:
    """Create a queued job and advance the graph one safe turn at a time."""

    def __init__(
        self,
        *,
        graph: WorkflowGraph,
        negotiation: NegotiationGateway,
        jobs: JobStore,
        invocations: InvocationStore,
        progress: ProgressStore,
        budget_guard: BudgetGuard,
        checkpoint_policy: CheckpointPolicy,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._graph = graph
        self._negotiation = negotiation
        self._jobs = jobs
        self._invocations = invocations
        self._progress = progress
        self._budget_guard = budget_guard
        self._checkpoint_policy = checkpoint_policy
        self._clock = clock
        self._uow = uow

    async def execute(self, request: StartSimulationRequest) -> StartSimulationResult:
        raise NotImplementedError("RunSimulationJob is implemented by issue #212")

    async def run(self, job_id: str) -> JobSnapshotResult:
        raise NotImplementedError("RunSimulationJob worker path is implemented by issue #212")


class StreamSimulationProgress:
    """Replay ordered progress events after ``Last-Event-ID``."""

    def __init__(self, *, progress: ProgressStore) -> None:
        self._progress = progress

    def execute(self, request: StreamSimulationProgressRequest) -> AsyncIterator[ProgressEventView]:
        raise NotImplementedError("StreamSimulationProgress is implemented by issue #213")


class PauseOrResumeSimulation:
    """Pause at a safe boundary and resume from the persisted checkpoint."""

    def __init__(
        self,
        *,
        jobs: JobStore,
        progress: ProgressStore,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._jobs = jobs
        self._progress = progress
        self._clock = clock
        self._uow = uow

    async def execute(self, request: PauseOrResumeSimulationRequest) -> PauseResumeResult:
        raise NotImplementedError("PauseOrResumeSimulation is implemented by issue #210")


class RecordAgentInvocation:
    """Write exactly one envelope for one LLM call; unique on ``invocation_id``."""

    def __init__(self, *, invocations: InvocationStore, prices: PriceTable, clock: Clock) -> None:
        self._invocations = invocations
        self._prices = prices
        self._clock = clock

    async def execute(self, request: RecordAgentInvocationRequest) -> InvocationRecordResult:
        raise NotImplementedError("RecordAgentInvocation is implemented by issue #208")


class GetJob:
    def __init__(self, *, jobs: JobStore, progress: ProgressStore) -> None:
        self._jobs = jobs
        self._progress = progress

    async def execute(self, request: GetJobRequest) -> JobSnapshotResult:
        raise NotImplementedError("GetJob is implemented by issue #216")


class CollectUsageReport:
    def __init__(self, *, invocations: InvocationStore) -> None:
        self._invocations = invocations

    async def execute(self, request: CollectUsageReportRequest) -> UsageReportResult:
        raise NotImplementedError("CollectUsageReport is implemented by issue #216")


class RegisterPromptTemplate:
    def __init__(
        self,
        *,
        registry: PromptRegistry,
        versioning: PromptVersioning,
        clock: Clock,
    ) -> None:
        self._registry = registry
        self._versioning = versioning
        self._clock = clock

    async def execute(self, request: RegisterPromptTemplateRequest) -> PromptTemplateResult:
        raise NotImplementedError("RegisterPromptTemplate is implemented by issue #214")


class ResolvePromptTemplate:
    def __init__(self, *, registry: PromptRegistry) -> None:
        self._registry = registry

    async def execute(self, request: ResolvePromptTemplateRequest) -> PromptTemplateResult:
        raise NotImplementedError("ResolvePromptTemplate is implemented by issue #214")
