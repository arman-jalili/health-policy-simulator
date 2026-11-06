"""SimulationOrchestration HTTP router — frozen API surface (ADR-004, issue #205).

The router is concrete by design: there is no separate HTTP interface. It is mounted by issue
#216; until then every handler raises the implementing issue's marker.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse

from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses
from simulation_orchestration.application.commands import (
    CollectUsageReportRequest,
    GetJobRequest,
    PauseOrResumeSimulationRequest,
    StartSimulationRequest,
    StreamSimulationProgressRequest,
)
from simulation_orchestration.application.dto import (
    JobSnapshotResult,
    PauseResumeResult,
    ProgressEventView,
)
from simulation_orchestration.application.values import (
    JobId,
    PauseAction,
    ProgressKind,
    RunBudget,
    RunId,
)
from simulation_orchestration.interfaces.http.deps import (
    SimulationOrchestrationContainer,
    get_container,
)
from simulation_orchestration.interfaces.http.schemas import (
    GraphStateBody,
    JobResponse,
    PauseResumeBody,
    PauseResumeResponse,
    RoundUsageItem,
    StakeholderUsageItem,
    StartBody,
    StartResponse,
    UsageResponse,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["simulation-orchestration"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)


def _budget(body: StartBody | PauseResumeBody) -> RunBudget:
    source = body.budget
    if source is None:
        return RunBudget()
    return RunBudget(
        max_invocations=source.max_invocations,
        max_tokens=source.max_tokens,
        max_cost=source.max_cost,
    )


@router.post(
    "/runs/{run_id}:start",
    response_model=StartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a simulation job",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def run_simulation_job(
    run_id: str,
    body: StartBody,
    container: Annotated[SimulationOrchestrationContainer, Depends(get_container)],
) -> StartResponse:
    result = await container.run_simulation_job.execute(
        StartSimulationRequest(run_id=RunId(run_id), budget=_budget(body))
    )
    return StartResponse(
        job_id=str(result.job_id), run_id=str(result.run_id), status=result.status.value
    )


@router.get(
    "/runs/{run_id}/stream",
    summary="Stream ordered progress events",
    openapi_extra={"x-required-scope": "runs:read"},
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "SSE progress stream"},
        **READ_ERRORS,
    },
)
async def stream_simulation_progress(
    run_id: str,
    container: Annotated[SimulationOrchestrationContainer, Depends(get_container)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    request = StreamSimulationProgressRequest(run_id=RunId(run_id), last_event_id=last_event_id)
    await container.stream_simulation_progress.validate(request)
    events = container.stream_simulation_progress.execute(request)
    return StreamingResponse(
        _sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/runs/{run_id}:pause",
    response_model=PauseResumeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pause at the next turn boundary",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def pause_or_resume_simulation(
    run_id: str,
    body: PauseResumeBody,
    container: Annotated[SimulationOrchestrationContainer, Depends(get_container)],
) -> PauseResumeResponse:
    action = PauseAction(body.action)
    result = await container.pause_or_resume_simulation.execute(
        PauseOrResumeSimulationRequest(
            run_id=RunId(run_id),
            action=action,
            reason=body.reason,
            budget=_budget(body) if body.budget is not None else None,
        )
    )
    return _pause_response(result)


@router.post(
    "/runs/{run_id}:resume",
    response_model=PauseResumeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Resume from the persisted checkpoint",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def resume_simulation(
    run_id: str,
    body: PauseResumeBody,
    container: Annotated[SimulationOrchestrationContainer, Depends(get_container)],
) -> PauseResumeResponse:
    result = await container.pause_or_resume_simulation.execute(
        PauseOrResumeSimulationRequest(
            run_id=RunId(run_id),
            action=PauseAction.RESUME,
            reason=body.reason,
            budget=_budget(body) if body.budget is not None else None,
        )
    )
    return _pause_response(result)


@router.get(
    "/runs/{run_id}/usage",
    response_model=UsageResponse,
    summary="Per-round and per-stakeholder token usage",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def collect_usage_report(
    run_id: str,
    container: Annotated[SimulationOrchestrationContainer, Depends(get_container)],
) -> UsageResponse:
    result = await container.collect_usage_report.execute(
        CollectUsageReportRequest(run_id=RunId(run_id))
    )
    return UsageResponse(
        run_id=str(result.run_id),
        total_invocations=result.total_invocations,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost=result.cost,
        by_stakeholder=[
            StakeholderUsageItem(
                stakeholder=item.stakeholder,
                invocations=item.invocations,
                input_tokens=item.input_tokens,
                output_tokens=item.output_tokens,
                cost=item.cost,
            )
            for item in result.by_stakeholder
        ],
        by_round=[
            RoundUsageItem(
                round=item.round,
                invocations=item.invocations,
                input_tokens=item.input_tokens,
                output_tokens=item.output_tokens,
                cost=item.cost,
            )
            for item in result.by_round
        ],
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Read job status, checkpoint and last error",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_job(
    job_id: str,
    container: Annotated[SimulationOrchestrationContainer, Depends(get_container)],
) -> JobResponse:
    result = await container.get_job.execute(GetJobRequest(job_id=JobId(job_id)))
    return _job_response(result)


def _pause_response(result: PauseResumeResult) -> PauseResumeResponse:
    checkpoint = result.checkpoint
    return PauseResumeResponse(
        run_id=str(result.run_id),
        status=result.status.value,
        checkpoint_round=checkpoint.round if checkpoint else None,
        checkpoint_phase=checkpoint.phase.value if checkpoint else None,
    )


def _job_response(result: JobSnapshotResult) -> JobResponse:
    state = result.checkpoint
    return JobResponse(
        job_id=str(result.job_id),
        run_id=str(result.run_id),
        status=result.status.value,
        attempts=result.attempts,
        checkpoint=GraphStateBody(
            run_id=str(state.run_id),
            round=state.round,
            phase=state.phase.value,
            next_actor=state.next_actor,
            budget_used_invocations=state.budget_used.invocations,
            budget_used_tokens=state.budget_used.tokens,
            budget_used_cost=state.budget_used.cost,
        ),
        error=result.error,
        progress_sequence=result.progress_sequence,
    )


async def _sse(events: AsyncIterator[ProgressEventView | str]) -> AsyncIterator[str]:
    async for frame in events:
        if isinstance(frame, str):
            yield frame
            continue
        data = json.dumps(
            {
                "event_id": frame.event_id,
                "run_id": str(frame.run_id),
                "sequence": frame.sequence,
                "kind": frame.kind.value,
                "payload": frame.payload,
            },
            default=str,
        )
        prefix = "" if frame.kind is ProgressKind.STREAM_CLOSED else f"id: {frame.event_id}\n"
        yield f"{prefix}event: {frame.kind.value}\ndata: {data}\n\n"
