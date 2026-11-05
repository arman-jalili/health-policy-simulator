"""Frozen application services of SimulationOrchestration (issue #205).

Canonical: .pi/architecture/modules/simulation-orchestration.md

Constructors, service names and ``execute`` signatures are frozen. Bodies raise
``NotImplementedError`` naming the issue that implements them; later issues may not rename or
remove a frozen member without a new freeze entry.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import asdict, replace
from decimal import Decimal
from typing import Any, cast

from shared.ids import new_id
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
    InvocationEnvelope,
    InvocationRecordResult,
    JobSnapshotResult,
    PauseResumeResult,
    ProgressEventView,
    PromptTemplateResult,
    StartSimulationResult,
    UsageReportResult,
)
from simulation_orchestration.application.errors import (
    InvalidJobTransition,
    PromptNotFound,
    SimulationRunNotFound,
)
from simulation_orchestration.application.events import RunPaused, RunResumed, SimulationEvent
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
    PauseBoundary,
    PromptVersioning,
)
from simulation_orchestration.application.values import (
    JobStatus,
    PauseAction,
    ProgressKind,
    RunId,
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

    async def _events(
        self, request: StreamSimulationProgressRequest
    ) -> AsyncIterator[ProgressEventView]:
        after = 0
        if request.last_event_id:
            previous = await self._progress.get(request.last_event_id)
            if previous is None or previous.run_id != request.run_id:
                raise ValueError(f"unknown Last-Event-ID {request.last_event_id!r}")
            after = previous.sequence
        while True:
            batch = list(await self._progress.list_after(request.run_id, after, request.limit))
            if not batch:
                return
            for event in batch:
                yield event
            if len(batch) < request.limit:
                return
            after = batch[-1].sequence

    def execute(self, request: StreamSimulationProgressRequest) -> AsyncIterator[ProgressEventView]:
        return self._events(request)


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
        job = await self._jobs.get_by_run(request.run_id)
        if job is None:
            raise SimulationRunNotFound(f"no simulation job for run {request.run_id}")
        if request.action is PauseAction.PAUSE:
            if job.status not in {JobStatus.QUEUED, JobStatus.RUNNING}:
                raise InvalidJobTransition(f"cannot pause a {job.status.value} job")
            decision = PauseBoundary().resolve(
                action=request.action, state=job.checkpoint, turn_committed=True
            )
            if not decision.accepted:
                raise InvalidJobTransition(decision.reason or "pause boundary rejected")
            paused = replace(job, status=JobStatus.PAUSED)
            await self._jobs.save(paused)
            paused_event = RunPaused(
                run_id=job.run_id,
                reason=request.reason,
                checkpoint=job.checkpoint,
            )
            await self._publish(job.run_id, ProgressKind.PAUSED, paused_event)
            return PauseResumeResult(
                run_id=job.run_id, status=JobStatus.PAUSED, checkpoint=job.checkpoint
            )
        if job.status is not JobStatus.PAUSED:
            raise InvalidJobTransition(f"cannot resume a {job.status.value} job")
        resumed = replace(
            job,
            status=JobStatus.RUNNING,
            claimed_by=None,
            updated_at=self._clock.now(),
        )
        await self._jobs.save(resumed)
        resumed_event = RunResumed(run_id=job.run_id, checkpoint=job.checkpoint)
        await self._publish(job.run_id, ProgressKind.RESUMED, resumed_event)
        return PauseResumeResult(
            run_id=job.run_id, status=JobStatus.RUNNING, checkpoint=job.checkpoint
        )

    async def _publish(self, run_id: RunId, kind: ProgressKind, event: SimulationEvent) -> None:
        sequence = await self._progress.latest_sequence(run_id) + 1
        await self._progress.append(
            ProgressEventView(
                event_id=new_id("evt"),
                run_id=run_id,
                sequence=sequence,
                kind=kind,
                payload=asdict(cast(Any, event)),
                created_at=self._clock.now(),
            )
        )


class RecordAgentInvocation:
    """Write exactly one envelope for one LLM call; unique on ``invocation_id``."""

    def __init__(self, *, invocations: InvocationStore, prices: PriceTable, clock: Clock) -> None:
        self._invocations = invocations
        self._prices = prices
        self._clock = clock

    async def execute(self, request: RecordAgentInvocationRequest) -> InvocationRecordResult:
        if request.input_tokens < 0 or request.output_tokens < 0:
            raise ValueError("token counts must not be negative")
        if request.latency_ms < 0:
            raise ValueError("latency must not be negative")
        price = self._prices.price_for(request.model)
        cost = (
            Decimal(request.input_tokens) * price.input_per_1k
            + Decimal(request.output_tokens) * price.output_per_1k
        ) / Decimal("1000")
        envelope = InvocationEnvelope(
            invocation_id=request.invocation_id,
            run_id=request.run_id,
            round=request.round,
            stakeholder=request.stakeholder,
            purpose=request.purpose,
            model=request.model,
            prompt=request.prompt,
            parameters=request.parameters,
            evidence_pack_ids=request.evidence_pack_ids,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            cost_estimate=cost,
            latency_ms=request.latency_ms,
            outcome=request.outcome,
            created_at=self._clock.now(),
        )
        await self._invocations.add(envelope)
        return InvocationRecordResult(
            invocation_id=envelope.invocation_id,
            run_id=envelope.run_id,
            prompt=envelope.prompt,
            cost_estimate=envelope.cost_estimate,
        )


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
        existing = await self._registry.list_versions(request.name)
        template = self._versioning.next_version(
            existing=existing, name=request.name, body=request.body
        )
        await self._registry.save(template)
        return PromptTemplateResult(
            id=str(template.id),
            name=template.name,
            version=template.version,
            body=template.body,
            checksum=template.checksum,
            created_at=template.created_at,
        )


class ResolvePromptTemplate:
    def __init__(self, *, registry: PromptRegistry) -> None:
        self._registry = registry

    async def execute(self, request: ResolvePromptTemplateRequest) -> PromptTemplateResult:
        if request.version is None:
            template = await self._registry.latest(request.name)
        else:
            template = await self._registry.get(request.name, request.version)
        if template is None:
            raise PromptNotFound(f"no prompt {request.name!r} at {request.version or 'latest'}")
        return PromptTemplateResult(
            id=str(template.id),
            name=template.name,
            version=template.version,
            body=template.body,
            checksum=template.checksum,
            created_at=template.created_at,
        )
