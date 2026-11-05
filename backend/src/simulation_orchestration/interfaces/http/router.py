"""SimulationOrchestration HTTP router — frozen API surface (ADR-004, issue #205).

The router is concrete by design: there is no separate HTTP interface. It is mounted by issue
#216; until then every handler raises the implementing issue's marker.
"""

from __future__ import annotations

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
from simulation_orchestration.application.values import JobId, PauseAction, RunBudget, RunId
from simulation_orchestration.interfaces.http.deps import (
    SimulationOrchestrationContainer,
    get_container,
)
from simulation_orchestration.interfaces.http.schemas import (
    JobResponse,
    PauseResumeBody,
    PauseResumeResponse,
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
    await container.run_simulation_job.execute(
        StartSimulationRequest(run_id=RunId(run_id), budget=_budget(body))
    )
    raise NotImplementedError("simulation-orchestration router is wired by issue #216")


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
    container.stream_simulation_progress.execute(
        StreamSimulationProgressRequest(run_id=RunId(run_id), last_event_id=last_event_id)
    )
    raise NotImplementedError("simulation-orchestration router is wired by issue #216")


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
    await container.pause_or_resume_simulation.execute(
        PauseOrResumeSimulationRequest(
            run_id=RunId(run_id),
            action=action,
            reason=body.reason,
            budget=_budget(body) if body.budget is not None else None,
        )
    )
    raise NotImplementedError("simulation-orchestration router is wired by issue #216")


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
    await container.pause_or_resume_simulation.execute(
        PauseOrResumeSimulationRequest(
            run_id=RunId(run_id),
            action=PauseAction.RESUME,
            reason=body.reason,
            budget=_budget(body) if body.budget is not None else None,
        )
    )
    raise NotImplementedError("simulation-orchestration router is wired by issue #216")


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
    await container.collect_usage_report.execute(CollectUsageReportRequest(run_id=RunId(run_id)))
    raise NotImplementedError("simulation-orchestration router is wired by issue #216")


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
    await container.get_job.execute(GetJobRequest(job_id=JobId(job_id)))
    raise NotImplementedError("simulation-orchestration router is wired by issue #216")
