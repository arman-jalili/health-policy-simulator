"""NegotiationSession HTTP router — frozen API surface (ADR-004, issue #282).

The router is concrete by design. Handlers forward to the container services and map frozen
DTOs to the OpenAPI schemas; business rules stay in the aggregate.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse

from identity_access.interfaces.http.dependencies import require_declared_scope
from negotiation_session.application.commands import (
    CloseRoundRequest,
    FormCoalitionRequest,
    GetSimulationRunRequest,
    ListConflictTopicsRequest,
    ListRoundLearningRequest,
    ListRoundsRequest,
    OpenRoundRequest,
    OpenSimulationRunRequest,
    RecordAbstentionRequest,
    ReplaySimulationHistoryRequest,
    RevisePositionRequest,
    SubmitInitialPositionRequest,
    TakeNegotiationTurnRequest,
)
from negotiation_session.application.dto import (
    ArgumentResult,
    CoalitionResult,
    ConflictTopicResult,
    OpenSimulationRunResult,
    PositionResult,
    ReplayResult,
    RoundLearningResult,
    RoundSummaryResult,
    SimulationRunResult,
)
from negotiation_session.application.progress import (
    SSE_MEDIA_TYPE,
    encode_frame,
    parse_last_event_id,
)
from negotiation_session.domain.entities import RoundLearning
from negotiation_session.domain.values import (
    ArgumentId,
    ArgumentStance,
    ClaimStatement,
    ConflictStatus,
    EvidencePackId,
    InvocationId,
    LearningId,
    LearningInsight,
    LearningInsightType,
    PositionId,
    Proposal,
    ProposalComponent,
    ProposalQuantification,
    RevisionReason,
    RunId,
    StakeholderId,
    TargetRef,
    TopicRef,
)
from negotiation_session.interfaces.http.deps import (
    NegotiationSessionContainer,
    get_container,
)
from negotiation_session.interfaces.http.schemas import (
    AbstentionBody,
    ArgumentResponse,
    BoundStakeholderBody,
    ClaimBody,
    CloseRoundBody,
    CloseRoundResponse,
    CoalitionBody,
    CoalitionOfferResponse,
    CoalitionResponse,
    ConflictListResponse,
    ConflictResponse,
    EventItem,
    EventsResponse,
    LearningInsightResponse,
    LearningListResponse,
    LearningResponse,
    OpenRoundBody,
    OpenRoundResponse,
    OpenRunBody,
    OpenRunResponse,
    PositionBody,
    PositionResponse,
    ProposalBody,
    ProposalComponentBody,
    ReviseBody,
    RevisionReasonResponse,
    RoundListResponse,
    RoundResponse,
    RunResponse,
    TargetBody,
    TurnBody,
)
from shared.errors import BadRequestError
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["negotiation-session"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)

Container = Annotated[NegotiationSessionContainer, Depends(get_container)]


def _proposal(body: ProposalBody) -> Proposal:
    return Proposal(
        summary=body.summary,
        components=tuple(
            ProposalComponent(
                measure=component.measure,
                effect=component.effect,
                population=component.population,
                cost_eur=component.cost_eur,
                quantification=ProposalQuantification(component.quantification),
                support_record=tuple(EvidencePackId(item) for item in component.support_record),
            )
            for component in body.components
        ),
    )


def _proposal_body(proposal: Proposal) -> ProposalBody:
    return ProposalBody(
        summary=proposal.summary,
        components=[
            ProposalComponentBody(
                measure=component.measure,
                effect=component.effect,
                population=component.population,
                cost_eur=component.cost_eur,
                quantification=component.quantification.value,
                support_record=[str(item) for item in component.support_record],
            )
            for component in proposal.components
        ],
    )


def _reason(body: ReviseBody) -> RevisionReason:
    return RevisionReason(
        argument_ids=tuple(ArgumentId(item) for item in body.reason.argument_ids),
        pack_ids=tuple(EvidencePackId(item) for item in body.reason.pack_ids),
        driver=body.reason.driver,
    )


def _run_response(result: SimulationRunResult) -> RunResponse:
    return RunResponse(
        run_id=str(result.run_id),
        phase=result.phase.value,
        round=result.round,
        round_cap=result.round_cap,
        closed=result.closed,
        bound_stakeholder_ids=[str(item) for item in result.bound_stakeholder_ids],
        open_position_ids=[str(item) for item in result.open_position_ids],
        coalition_ids=[str(item) for item in result.coalition_ids],
    )


def _open_run_response(result: OpenSimulationRunResult) -> OpenRunResponse:
    return OpenRunResponse(
        run_id=str(result.run_id),
        phase=result.phase.value,
        mandate_hash=result.mandate.mandate_hash,
        bound=[
            BoundStakeholderBody(
                stakeholder_id=str(item.stakeholder_id),
                institution_name=item.institution_name,
                institution_code=item.institution_code,
                profile_version=item.profile_version,
                persona_version=item.persona_version,
            )
            for item in result.bound
        ],
    )


def _position_response(result: PositionResult) -> PositionResponse:
    return PositionResponse(
        position_id=str(result.position_id),
        run_id=str(result.run_id),
        round=result.round,
        stakeholder_id=str(result.stakeholder_id),
        topic=str(result.topic),
        stance=result.stance.value,
        proposal=_proposal_body(result.proposal),
        evidence_ids=[str(item) for item in result.evidence_ids],
        supersedes=str(result.supersedes) if result.supersedes is not None else None,
        revision=(
            RevisionReasonResponse(
                argument_ids=[str(item) for item in result.revision.argument_ids],
                pack_ids=[str(item) for item in result.revision.pack_ids],
                driver=result.revision.driver,
            )
            if result.revision is not None
            else None
        ),
    )


def _argument_response(result: ArgumentResult) -> ArgumentResponse:
    return ArgumentResponse(
        argument_id=str(result.argument_id),
        run_id=str(result.run_id),
        round=result.round,
        stakeholder_id=str(result.stakeholder_id),
        target=TargetBody(
            topic=str(result.target.topic),
            position_id=(
                str(result.target.position_id) if result.target.position_id is not None else None
            ),
            argument_id=(
                str(result.target.argument_id) if result.target.argument_id is not None else None
            ),
        ),
        stance=result.stance.value,
        evidence_ids=[str(item) for item in result.evidence_ids],
        unsupported=result.unsupported,
        invocation_id=str(result.invocation_id) if result.invocation_id else None,
    )


def _conflict_response(result: ConflictTopicResult) -> ConflictResponse:
    return ConflictResponse(
        conflict_id=str(result.conflict_id),
        run_id=str(result.run_id),
        topic=str(result.topic),
        status=result.status.value,
        stances={str(key): value.value for key, value in result.stances.items()},
    )


def _coalition_response(result: CoalitionResult) -> CoalitionResponse:
    return CoalitionResponse(
        coalition_id=str(result.coalition_id),
        run_id=str(result.run_id),
        topic=str(result.topic),
        proposal=_proposal_body(result.proposal),
        members=[str(item) for item in result.members],
        offers=[
            CoalitionOfferResponse(
                offer_id=str(offer.offer_id),
                invited_id=str(offer.invited_id),
                conditions=offer.conditions,
                status=offer.status.value,
                decline_reason=offer.decline_reason,
            )
            for offer in result.offers
        ],
    )


def _learning_response(result: RoundLearningResult) -> LearningResponse:
    return LearningResponse(
        learning_id=str(result.learning_id),
        run_id=str(result.run_id),
        round=result.round,
        insights=[
            LearningInsightResponse(
                insight_type=insight.insight_type,
                statement=insight.statement,
                derived_from=[str(item) for item in insight.derived_from],
                round_number=insight.round_number,
            )
            for insight in result.insights
        ],
    )


def _round_response(result: RoundSummaryResult) -> RoundResponse:
    return RoundResponse(
        round=result.round,
        closed=result.closed,
        argument_count=result.argument_count,
        abstention_count=result.abstention_count,
        learning=_learning_response(result.learning) if result.learning is not None else None,
    )


def _events_response(result: ReplayResult) -> EventsResponse:
    return EventsResponse(
        items=[
            EventItem(
                sequence=item.sequence,
                event_type=item.event_type,
                payload={str(key): value for key, value in item.payload.items()},
                occurred_at=item.occurred_at.isoformat() if item.occurred_at else None,
            )
            for item in result.events
        ],
        state=_run_response(result.state),
    )


@router.post(
    "/runs",
    response_model=OpenRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Open a negotiation run from a policy question",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def open_simulation_run(body: OpenRunBody, container: Container) -> OpenRunResponse:
    result = await container.open_simulation_run.execute(
        OpenSimulationRunRequest(
            question=body.question,
            round_cap=body.round_cap or 5,
            stakeholder_ids=tuple(StakeholderId(item) for item in (body.stakeholder_ids or ())),
            consensus_threshold=body.consensus_threshold,
        )
    )
    return _open_run_response(result)


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    summary="Read the current run state",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_simulation_run(run_id: str, container: Container) -> RunResponse:
    result = await container.get_simulation_run.execute(
        GetSimulationRunRequest(run_id=RunId(run_id))
    )
    return _run_response(result)


@router.get(
    "/runs/{run_id}/events",
    response_model=EventsResponse,
    summary="Replay the ordered run log",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def replay_simulation_history(
    run_id: str, container: Container, until_round: int | None = None
) -> EventsResponse:
    result = await container.replay_simulation_history.execute(
        ReplaySimulationHistoryRequest(run_id=RunId(run_id), until_round=until_round)
    )
    return _events_response(result)


@router.get(
    "/runs/{run_id}/rounds",
    response_model=RoundListResponse,
    summary="List rounds with their learning summaries",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_rounds(
    run_id: str, container: Container, cursor: str | None = None, limit: int = 50
) -> RoundListResponse:
    rounds = await container.list_rounds.execute(
        ListRoundsRequest(run_id=RunId(run_id), cursor=cursor, limit=limit)
    )
    return RoundListResponse(items=[_round_response(item) for item in rounds])


@router.post(
    "/runs/{run_id}/rounds",
    response_model=OpenRoundResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open the next negotiation round",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def open_round(
    run_id: str, container: Container, body: OpenRoundBody | None = None
) -> OpenRoundResponse:
    result = await container.open_round.execute(OpenRoundRequest(run_id=RunId(run_id)))
    return OpenRoundResponse(
        run_id=str(result.run_id),
        round=result.round,
        closed=result.closed,
        turn_order=[str(item) for item in result.turn_order],
    )


@router.post(
    "/runs/{run_id}/rounds/{number}:close",
    response_model=CloseRoundResponse,
    summary="Close a round with its learning and evaluate stopping",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def close_round(
    run_id: str, number: int, body: CloseRoundBody, container: Container
) -> CloseRoundResponse:
    current = await container.get_simulation_run.execute(
        GetSimulationRunRequest(run_id=RunId(run_id))
    )
    insights = tuple(
        LearningInsight(
            insight_type=LearningInsightType(item.insight_type),
            statement=item.statement,
            derived_from=tuple(ArgumentId(argument) for argument in item.derived_from),
            round_number=item.round_number,
        )
        for item in body.learning
    )
    learning = RoundLearning.capture(
        learning_id=LearningId(f"lrn_{RunId(run_id)}_{number}"),
        round_number=current.round,
        insights=insights,
    )
    result = await container.close_round.execute(
        CloseRoundRequest(run_id=RunId(run_id), learning=learning, convergence=body.convergence)
    )
    return CloseRoundResponse(
        run_id=str(result.run_id),
        round=result.round,
        learning=_learning_response(result.learning),
        stopping_condition={
            "name": result.stopping_condition.name.value,
            "fired": result.stopping_condition.fired,
            "parameters": dict(result.stopping_condition.parameters),
        },
    )


@router.post(
    "/runs/{run_id}/positions",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an evidenced initial position",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def submit_initial_position(
    run_id: str, body: PositionBody, container: Container
) -> PositionResponse:
    result = await container.submit_initial_position.execute(
        SubmitInitialPositionRequest(
            run_id=RunId(run_id),
            stakeholder_id=StakeholderId(body.stakeholder_id),
            topic=TopicRef(body.topic),
            stance=ArgumentStance(body.stance),
            proposal=_proposal(body.proposal),
            evidence_ids=tuple(EvidencePackId(item) for item in body.evidence_ids),
        )
    )
    return _position_response(result)


@router.post(
    "/runs/{run_id}/turns",
    response_model=ArgumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Take a negotiation turn with evidence",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def take_negotiation_turn(
    run_id: str, body: TurnBody, container: Container
) -> ArgumentResponse:
    result = await container.take_negotiation_turn.execute(
        TakeNegotiationTurnRequest(
            run_id=RunId(run_id),
            stakeholder_id=StakeholderId(body.stakeholder_id),
            target=_target(body.target),
            stance=ArgumentStance(body.stance),
            text=body.text,
            claims=tuple(_claim(item) for item in body.claims),
            evidence_ids=tuple(EvidencePackId(item) for item in body.evidence_ids),
            unsupported=body.unsupported,
            invocation_id=(InvocationId(body.invocation_id) if body.invocation_id else None),
        )
    )
    return _argument_response(result)


def _target(body: TargetBody) -> TargetRef:
    return TargetRef(
        topic=TopicRef(body.topic),
        position_id=PositionId(body.position_id) if body.position_id else None,
        argument_id=ArgumentId(body.argument_id) if body.argument_id else None,
    )


def _claim(body: ClaimBody) -> ClaimStatement:
    return ClaimStatement(text=body.text, claim_id=body.claim_id, verdict=body.verdict)


@router.post(
    "/runs/{run_id}/positions/{position_id}:revise",
    response_model=PositionResponse,
    summary="Revise a position with a causal reason",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def revise_position(
    run_id: str, position_id: str, body: ReviseBody, container: Container
) -> PositionResponse:
    result = await container.revise_position.execute(
        RevisePositionRequest(
            run_id=RunId(run_id),
            position_id=PositionId(position_id),
            stance=ArgumentStance(body.stance),
            reason=_reason(body),
        )
    )
    return _position_response(result)


@router.post(
    "/runs/{run_id}/abstentions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record an abstention for a bound stakeholder",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def record_abstention(run_id: str, body: AbstentionBody, container: Container) -> None:
    await container.record_abstention.execute(
        RecordAbstentionRequest(
            run_id=RunId(run_id),
            stakeholder_id=StakeholderId(body.stakeholder_id),
            topic=TopicRef(body.topic),
        )
    )


@router.get(
    "/runs/{run_id}/conflicts",
    response_model=ConflictListResponse,
    summary="List tracked conflict topics",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_conflict_topics(
    run_id: str, container: Container, status: str | None = None
) -> ConflictListResponse:
    conflicts = await container.list_conflict_topics.execute(
        ListConflictTopicsRequest(
            run_id=RunId(run_id),
            status=ConflictStatus(status) if status else None,
        )
    )
    return ConflictListResponse(items=[_conflict_response(item) for item in conflicts])


@router.post(
    "/runs/{run_id}/coalitions",
    response_model=CoalitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Form a coalition behind one shared proposal",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def form_coalition(
    run_id: str, body: CoalitionBody, container: Container
) -> CoalitionResponse:
    result = await container.form_coalition.execute(
        FormCoalitionRequest(
            run_id=RunId(run_id),
            topic=TopicRef(body.topic),
            member_ids=tuple(StakeholderId(item) for item in body.member_ids),
            proposal=_proposal(body.proposal),
        )
    )
    return _coalition_response(result)


@router.get(
    "/runs/{run_id}/learning",
    response_model=LearningListResponse,
    summary="List per-round learning",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_round_learning(run_id: str, container: Container) -> LearningListResponse:
    items = await container.list_round_learning.execute(
        ListRoundLearningRequest(run_id=RunId(run_id))
    )
    return LearningListResponse(items=[_learning_response(item) for item in items])


@router.get(
    "/runs/{run_id}/negotiation/stream",
    summary="Live ordered event stream with Last-Event-ID replay",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def stream_run(
    run_id: str,
    container: Container,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    try:
        parse_last_event_id(last_event_id)
    except ValueError as error:
        raise BadRequestError(str(error)) from error
    frames = container.progress_stream.subscribe(RunId(run_id), last_event_id=last_event_id)

    async def encode() -> AsyncIterator[str]:
        async for frame in frames:
            yield encode_frame(frame)

    return StreamingResponse(
        encode(),
        media_type=SSE_MEDIA_TYPE,
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


__all__ = ["router"]
