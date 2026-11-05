"""GovernanceCompliance HTTP router — wired API surface (ADR-004, issue #259)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from governance_compliance.application.commands import (
    DisclosePositionProvenanceRequest,
    EnforceInstitutionOnlyOutputRequest,
    GetPositionProvenanceRequest,
    ListAllowlistRequest,
    ListViolationsRequest,
)
from governance_compliance.application.dto import ViolationRecord
from governance_compliance.application.values import (
    InvocationId,
    PositionId,
    RunId,
    SpeakerKind,
    ViolationClass,
)
from governance_compliance.interfaces.http.deps import GovernanceContainer, get_container
from governance_compliance.interfaces.http.schemas import (
    AllowlistItem,
    AllowlistResponse,
    DiscloseProvenanceBody,
    GuardCheckBody,
    GuardCheckResponse,
    ProvenanceResponse,
    ViolationItem,
    ViolationListResponse,
)
from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["governance-compliance"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)


def _violation_item(item: ViolationRecord) -> ViolationItem:
    return ViolationItem(
        violation_id=str(item.violation_id),
        violation_class=item.violation_class.value,
        offending_span=item.offending_span,
        rewritten_span=item.rewritten_span,
        rule_id=item.rule_id.value,
        rule_version=item.rule_version,
        detected_at=item.detected_at,
    )


@router.post(
    "/governance/check",
    response_model=GuardCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Guard one agent output before persistence",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def enforce_institution_only_output(
    body: GuardCheckBody,
    container: Annotated[GovernanceContainer, Depends(get_container)],
) -> GuardCheckResponse:
    result = await container.enforce_institution_only_output.execute(
        EnforceInstitutionOnlyOutputRequest(
            text=body.text,
            speaker_kind=SpeakerKind(body.speaker_kind),
            invocation_id=InvocationId(body.invocation_id),
            run_id=RunId(body.run_id) if body.run_id is not None else None,
            position_id=PositionId(body.position_id) if body.position_id is not None else None,
            cited_passage_ids=tuple(body.cited_passage_ids),
            reference_figure_ids=tuple(body.reference_figure_ids),
        )
    )
    return GuardCheckResponse(
        decision=result.decision.value,
        violations=[_violation_item(item) for item in result.violations],
        rewritten_text=result.rewritten_text,
        rule_version=result.rule_version,
    )


@router.get(
    "/governance/violations",
    response_model=ViolationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persisted governance violations",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_violations(
    container: Annotated[GovernanceContainer, Depends(get_container)],
    run_id: str | None = None,
    violation_class: str | None = Query(default=None, alias="class"),
    limit: int = Query(default=100, ge=1, le=500),
) -> ViolationListResponse:
    result = await container.list_violations.execute(
        ListViolationsRequest(
            run_id=RunId(run_id) if run_id is not None else None,
            violation_class=ViolationClass(violation_class)
            if violation_class is not None
            else None,
            limit=limit,
        )
    )
    return ViolationListResponse(items=[_violation_item(item) for item in result.items])


@router.get(
    "/positions/{position_id}/provenance",
    response_model=ProvenanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Read the disclosed provenance of one position",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_position_provenance(
    position_id: str,
    container: Annotated[GovernanceContainer, Depends(get_container)],
    version: int | None = Query(default=None, ge=1),
) -> ProvenanceResponse:
    result = await container.get_position_provenance.execute(
        GetPositionProvenanceRequest(position_id=PositionId(position_id), version=version)
    )
    record = result.record
    return ProvenanceResponse(
        position_id=str(record.position_id),
        evidence_ids=list(record.evidence_ids),
        argument_ids=list(record.argument_ids),
        invocation_id=record.invocation_id,
        prompt_version=record.prompt_version,
        model=record.model,
        disclosed_at=record.disclosed_at,
        version=record.version,
    )


@router.post(
    "/positions/{position_id}/provenance",
    response_model=ProvenanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Disclose provenance for one position",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def disclose_position_provenance(
    position_id: str,
    body: DiscloseProvenanceBody,
    container: Annotated[GovernanceContainer, Depends(get_container)],
) -> ProvenanceResponse:
    result = await container.disclose_position_provenance.execute(
        DisclosePositionProvenanceRequest(
            position_id=PositionId(position_id),
            version=body.version,
            requested_by=body.requested_by,
        )
    )
    record = result.record
    return ProvenanceResponse(
        position_id=str(record.position_id),
        evidence_ids=list(record.evidence_ids),
        argument_ids=list(record.argument_ids),
        invocation_id=record.invocation_id,
        prompt_version=record.prompt_version,
        model=record.model,
        disclosed_at=record.disclosed_at,
        version=record.version,
    )


@router.get(
    "/governance/allowlist",
    response_model=AllowlistResponse,
    status_code=status.HTTP_200_OK,
    summary="List the canonical institutions-only allowlist",
    openapi_extra={"x-required-scope": "admin"},
    responses=READ_ERRORS,
)
async def list_allowlist(
    container: Annotated[GovernanceContainer, Depends(get_container)],
) -> AllowlistResponse:
    result = await container.list_allowlist.execute(ListAllowlistRequest())
    return AllowlistResponse(
        institutions=[
            AllowlistItem(
                code=item.code,
                canonical_name=item.canonical_name,
                short_name=item.short_name,
                category=item.category,
                aliases=list(item.aliases),
            )
            for item in result.institutions
        ],
        version=result.version,
    )
