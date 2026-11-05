"""ClaimValidation HTTP router — frozen API surface (ADR-004, issue #164)."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status

from claim_validation.application.commands import (
    FlagUnsupportedAssertionRequest,
    GetClaimRequest,
    ListContradictionsRequest,
    ListReferenceFiguresRequest,
    RegisterReferenceFigureRequest,
    ResolveExpertReviewRequest,
    VerifyClaimRequest,
)
from claim_validation.domain.values import ClaimId, ClaimType, MeasureReference, VerificationVerdict
from claim_validation.interfaces.http.deps import ClaimValidationContainer, get_container
from claim_validation.interfaces.http.schemas import (
    ClaimDetailResponse,
    ClaimVerdictResponse,
    ContradictionItem,
    ContradictionResponse,
    FlagBody,
    MeasureBody,
    ReferenceFigureBody,
    ReferenceFigureItem,
    ReferenceFigureResponse,
    ReferenceFiguresResponse,
    ReviewBody,
    VerifyClaimBody,
)
from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["claim-validation"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)


def _measure(body: MeasureBody | None) -> MeasureReference | None:
    if body is None:
        return None
    return MeasureReference(body.measure, body.unit, body.period, body.geography)


@router.post(
    "/claims:verify",
    response_model=ClaimVerdictResponse,
    summary="Verify one claim by type",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def verify_claim(
    body: VerifyClaimBody,
    container: Annotated[ClaimValidationContainer, Depends(get_container)],
) -> ClaimVerdictResponse:
    result = await container.verify_claim.execute(
        VerifyClaimRequest(
            text=body.text,
            claim_type=ClaimType(body.claim_type) if body.claim_type else None,
            measure=_measure(body.measure),
            asserted_value=Decimal(body.asserted_value) if body.asserted_value else None,
        )
    )
    return ClaimVerdictResponse(
        claim_id=result.claim_id,
        verdict=result.verdict.value,
        path=result.path.value,
        claim_type=result.claim_type.value,
        sources=list(result.sources),
        delta=str(result.delta) if result.delta is not None else None,
    )


@router.post(
    "/claims/{claim_id}:flag",
    response_model=ClaimVerdictResponse,
    summary="Mark an assertion unsupported without dropping it",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def flag_unsupported_assertion(
    claim_id: str,
    body: FlagBody,
    container: Annotated[ClaimValidationContainer, Depends(get_container)],
) -> ClaimVerdictResponse:
    result = await container.flag_unsupported.execute(
        FlagUnsupportedAssertionRequest(ClaimId(claim_id), body.reason)
    )
    return ClaimVerdictResponse(
        claim_id=result.claim_id,
        verdict=result.verdict.value,
        path=result.path.value,
        claim_type=result.claim_type.value,
        sources=list(result.sources),
        delta=str(result.delta) if result.delta is not None else None,
    )


@router.get(
    "/claims/{claim_id}",
    response_model=ClaimDetailResponse,
    summary="Read a claim with its verification and review",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_claim(
    claim_id: str,
    container: Annotated[ClaimValidationContainer, Depends(get_container)],
) -> ClaimDetailResponse:
    result = await container.get_claim.execute(GetClaimRequest(ClaimId(claim_id)))
    return ClaimDetailResponse(
        claim_id=result.claim_id,
        text=result.text,
        verdict=result.verdict.value,
        path=result.path.value if result.path is not None else "qualitative",
        claim_type=result.claim_type.value,
        sources=list(result.sources),
        review_verdict=result.review_verdict.value if result.review_verdict else None,
        review_basis=result.review_basis,
    )


@router.post(
    "/reference-figures",
    status_code=status.HTTP_201_CREATED,
    response_model=ReferenceFigureResponse,
    summary="Register an authoritative reference figure",
    openapi_extra={"x-required-scope": "corpus:write"},
    responses=WRITE_ERRORS,
)
async def register_reference_figure(
    body: ReferenceFigureBody,
    container: Annotated[ClaimValidationContainer, Depends(get_container)],
) -> ReferenceFigureResponse:
    result = await container.register_reference_figure.execute(
        RegisterReferenceFigureRequest(
            measure=MeasureReference(
                body.measure.measure,
                body.measure.unit,
                body.measure.period,
                body.measure.geography,
            ),
            value=__import__("decimal").Decimal(body.value),
            tier=body.tier,
            as_of=body.as_of,
            source_id=body.source_id,
        )
    )
    return ReferenceFigureResponse(figure_id=result.figure_id)


@router.get(
    "/reference-figures",
    response_model=ReferenceFiguresResponse,
    summary="List reference figures",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_reference_figures(
    container: Annotated[ClaimValidationContainer, Depends(get_container)],
) -> ReferenceFiguresResponse:
    items = await container.list_reference_figures.execute(ListReferenceFiguresRequest())
    return ReferenceFiguresResponse(
        items=[
            ReferenceFigureItem(
                figure_id=item.figure_id,
                measure=item.measure,
                unit=item.unit,
                period=item.period,
                geography=item.geography,
                value=str(item.value),
                tier=item.tier,
                as_of=item.as_of,
                source_id=item.source_id,
            )
            for item in items
        ]
    )


@router.get(
    "/contradictions",
    response_model=ContradictionResponse,
    summary="List contradiction findings",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_contradictions(
    container: Annotated[ClaimValidationContainer, Depends(get_container)],
) -> ContradictionResponse:
    items = await container.list_contradictions.execute(ListContradictionsRequest())
    return ContradictionResponse(
        items=[
            ContradictionItem(
                finding_id=item.finding_id,
                claim_id_a=item.claim_id_a,
                claim_id_b=item.claim_id_b,
                measure=item.measure,
                delta=str(item.delta),
            )
            for item in items
        ]
    )


@router.post(
    "/claims/{claim_id}/reviews",
    response_model=ClaimVerdictResponse,
    summary="Resolve an escalated claim",
    openapi_extra={"x-required-scope": "admin"},
    responses=WRITE_ERRORS,
)
async def resolve_expert_review(
    claim_id: str,
    body: ReviewBody,
    container: Annotated[ClaimValidationContainer, Depends(get_container)],
) -> ClaimVerdictResponse:
    result = await container.resolve_expert_review.execute(
        ResolveExpertReviewRequest(
            ClaimId(claim_id),
            VerificationVerdict(body.verdict),
            body.basis,
        )
    )
    return ClaimVerdictResponse(
        claim_id=result.claim_id,
        verdict=result.verdict.value,
        path=result.path.value,
        claim_type=result.claim_type.value,
        sources=list(result.sources),
        delta=str(result.delta) if result.delta is not None else None,
    )
