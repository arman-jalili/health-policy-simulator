"""NegotiationSession HTTP router — frozen API surface (ADR-004, issue #282).

The router is concrete by design: there is no separate HTTP interface file. It is mounted by
issue #299; until then every handler raises the implementing issue's marker.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse

from identity_access.interfaces.http.dependencies import require_declared_scope
from negotiation_session.interfaces.http.schemas import (
    AbstentionBody,
    ArgumentResponse,
    CoalitionBody,
    CoalitionResponse,
    ConflictListResponse,
    EventsResponse,
    LearningListResponse,
    OpenRunBody,
    OpenRunResponse,
    PositionBody,
    PositionResponse,
    ReviseBody,
    RoundListResponse,
    RunResponse,
    TurnBody,
)
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["negotiation-session"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)


@router.post(
    "/runs",
    response_model=OpenRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Open a negotiation run from a policy question",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def open_simulation_run(body: OpenRunBody) -> OpenRunResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    summary="Read the current run state",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_simulation_run(run_id: str) -> RunResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.get(
    "/runs/{run_id}/events",
    response_model=EventsResponse,
    summary="Replay the ordered run log",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def replay_simulation_history(run_id: str, until_round: int | None = None) -> EventsResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.get(
    "/runs/{run_id}/rounds",
    response_model=RoundListResponse,
    summary="List rounds with their learning summaries",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_rounds(run_id: str, cursor: str | None = None, limit: int = 50) -> RoundListResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.post(
    "/runs/{run_id}/positions",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an evidenced initial position",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def submit_initial_position(run_id: str, body: PositionBody) -> PositionResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.post(
    "/runs/{run_id}/turns",
    response_model=ArgumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Take a negotiation turn with evidence",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def take_negotiation_turn(run_id: str, body: TurnBody) -> ArgumentResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.post(
    "/runs/{run_id}/positions/{position_id}:revise",
    response_model=PositionResponse,
    summary="Revise a position with a causal reason",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def revise_position(run_id: str, position_id: str, body: ReviseBody) -> PositionResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.post(
    "/runs/{run_id}/abstentions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record an abstention for a bound stakeholder",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def record_abstention(run_id: str, body: AbstentionBody) -> None:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.get(
    "/runs/{run_id}/conflicts",
    response_model=ConflictListResponse,
    summary="List tracked conflict topics",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_conflict_topics(run_id: str, status: str | None = None) -> ConflictListResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.post(
    "/runs/{run_id}/coalitions",
    response_model=CoalitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Form a coalition behind one shared proposal",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def form_coalition(run_id: str, body: CoalitionBody) -> CoalitionResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.get(
    "/runs/{run_id}/learning",
    response_model=LearningListResponse,
    summary="List per-round learning",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_round_learning(run_id: str) -> LearningListResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #299")


@router.get(
    "/runs/{run_id}/stream",
    summary="Live ordered event stream with Last-Event-ID replay",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def stream_run(
    run_id: str,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    raise NotImplementedError("negotiation-session router is implemented by issue #298")
