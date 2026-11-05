"""StakeholderModel HTTP router — the frozen API surface (ADR-004).

Canonical: .pi/architecture/modules/stakeholder-model.md

Routes, scopes, payload shapes and error envelopes are the contract. Every handler delegates to a
use case in the container; the container is wired and mounted by the wiring issue (#117). Keeping
the router concrete here (no separate handler interface) is deliberate.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses
from stakeholder_model.application.commands import (
    BindAgentPersonaRequest,
    ListHistoricalPositionsRequest,
    ListStakeholdersRequest,
    SelectRelevantStakeholdersRequest,
)
from stakeholder_model.domain.values import RunId, StakeholderId
from stakeholder_model.interfaces.http.deps import StakeholderModelContainer, get_container
from stakeholder_model.interfaces.http.mappers import (
    to_cite_request,
    to_position_response,
    to_record_request,
    to_register_request,
    to_summary_response,
    to_update_request,
)
from stakeholder_model.interfaces.http.schemas import (
    BindBody,
    BindingResponse,
    BindResponse,
    CitePowerSourceBody,
    CitePowerSourceResponse,
    HistoricalPositionBody,
    HistoricalPositionsResponse,
    RegisterStakeholderBody,
    RegisterStakeholderResponse,
    SelectionBody,
    SelectionItem,
    SelectionResponse,
    StakeholdersResponse,
    UpdateProfileBody,
    UpdateProfileResponse,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["stakeholder-model"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)


@router.get(
    "/stakeholders",
    response_model=StakeholdersResponse,
    summary="List registered institutions",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_stakeholders(
    container: Annotated[StakeholderModelContainer, Depends(get_container)],
) -> StakeholdersResponse:
    """Return the registry with profile summaries."""
    summaries = await container.list_stakeholders.execute(ListStakeholdersRequest())
    return StakeholdersResponse(items=[to_summary_response(item) for item in summaries])


@router.post(
    "/stakeholders",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterStakeholderResponse,
    summary="Register an institution",
    openapi_extra={"x-required-scope": "admin"},
    responses=WRITE_ERRORS,
)
async def register_stakeholder(
    body: RegisterStakeholderBody,
    container: Annotated[StakeholderModelContainer, Depends(get_container)],
) -> RegisterStakeholderResponse:
    """Validate the persona profile and register the institution."""
    result = await container.register_stakeholder.execute(to_register_request(body))
    return RegisterStakeholderResponse(
        stakeholder_id=result.stakeholder_id,
        profile_version=result.profile_version,
    )


@router.patch(
    "/stakeholders/{stakeholder_id}",
    response_model=UpdateProfileResponse,
    summary="Update a profile for future runs",
    openapi_extra={"x-required-scope": "admin"},
    responses=WRITE_ERRORS,
)
async def update_profile(
    stakeholder_id: str,
    body: UpdateProfileBody,
    container: Annotated[StakeholderModelContainer, Depends(get_container)],
) -> UpdateProfileResponse:
    """Apply a profile revision; active bindings stay immutable."""
    result = await container.update_profile.execute(to_update_request(stakeholder_id, body))
    return UpdateProfileResponse(
        stakeholder_id=result.stakeholder_id,
        profile_version=result.profile_version,
        changed_fields=list(result.changed_fields),
    )


@router.post(
    "/stakeholders/{stakeholder_id}/powers",
    response_model=CitePowerSourceResponse,
    summary="Cite or refuse authority for a power claim",
    openapi_extra={"x-required-scope": "admin"},
    responses=WRITE_ERRORS,
)
async def cite_power_source(
    stakeholder_id: str,
    body: CitePowerSourceBody,
    container: Annotated[StakeholderModelContainer, Depends(get_container)],
) -> CitePowerSourceResponse:
    """Ground a veto/mandate/budget claim or return an explicit refusal."""
    result = await container.cite_power_source.execute(to_cite_request(stakeholder_id, body))
    return CitePowerSourceResponse(accepted=result.accepted, reason=result.reason)


@router.get(
    "/stakeholders/{stakeholder_id}/history",
    response_model=HistoricalPositionsResponse,
    summary="List attributed historical positions",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_historical_positions(
    stakeholder_id: str,
    usable_only: bool,
    container: Annotated[StakeholderModelContainer, Depends(get_container)],
) -> HistoricalPositionsResponse:
    """Return provenance-backed positions, optionally usable-only."""
    result = await container.list_positions.execute(
        ListHistoricalPositionsRequest(
            stakeholder_id=StakeholderId(stakeholder_id),
            usable_only=usable_only,
        )
    )
    return HistoricalPositionsResponse(
        stakeholder_id=result.stakeholder_id,
        positions=[to_position_response(item) for item in result.positions],
    )


@router.post(
    "/stakeholders/{stakeholder_id}/history",
    status_code=status.HTTP_201_CREATED,
    response_model=HistoricalPositionsResponse,
    summary="Record one attributed historical position",
    openapi_extra={"x-required-scope": "corpus:write"},
    responses=WRITE_ERRORS,
)
async def record_historical_position(
    stakeholder_id: str,
    body: HistoricalPositionBody,
    container: Annotated[StakeholderModelContainer, Depends(get_container)],
) -> HistoricalPositionsResponse:
    """Record a position; weak attribution is stored unusable."""
    result = await container.record_position.execute(to_record_request(stakeholder_id, body))
    return HistoricalPositionsResponse(
        stakeholder_id=stakeholder_id,
        positions=[to_position_response(result)],
    )


@router.post(
    "/runs/{run_id}/stakeholders:select",
    response_model=SelectionResponse,
    summary="Select institutions material to a mandate",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def select_relevant_stakeholders(
    run_id: str,
    body: SelectionBody,
    container: Annotated[StakeholderModelContainer, Depends(get_container)],
) -> SelectionResponse:
    """Score all institutions and return materiality in [0, 1]."""
    result = await container.select_stakeholders.execute(
        SelectRelevantStakeholdersRequest(run_id=RunId(run_id), mandate=body.mandate)
    )
    return SelectionResponse(
        items=[
            SelectionItem(
                stakeholder_id=selection.stakeholder_id,
                materiality=selection.materiality.value,
            )
            for selection in result.selections
        ]
    )


@router.post(
    "/runs/{run_id}/stakeholders:bind",
    response_model=BindResponse,
    summary="Bind selected institutions to immutable personas",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def bind_agent_persona(
    run_id: str,
    body: BindBody,
    container: Annotated[StakeholderModelContainer, Depends(get_container)],
) -> BindResponse:
    """Bind complete, institutions-only profiles for the run."""
    result = await container.bind_persona.execute(
        BindAgentPersonaRequest(
            run_id=RunId(run_id),
            stakeholder_ids=tuple(StakeholderId(value) for value in body.stakeholder_ids),
        )
    )
    return BindResponse(
        bindings=[
            BindingResponse(
                binding_id=binding.binding_id,
                stakeholder_id=binding.stakeholder_id,
                persona_version=binding.persona_version,
            )
            for binding in result.bindings
        ]
    )
