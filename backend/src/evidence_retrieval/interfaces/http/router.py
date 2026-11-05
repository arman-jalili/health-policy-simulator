"""EvidenceRetrieval HTTP router — the frozen API surface (ADR-004).

Canonical: .pi/architecture/modules/evidence-retrieval.md

Routes, scopes, payload shapes and error envelopes are the contract. Every handler delegates to a
use case in the application container; the container is wired by the wiring issue. The router is
deliberately not mounted in ``shared.app`` until then, so a TODO body cannot answer a real request.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from evidence_retrieval.application.commands import (
    ApplyRecencyPolicyRequest,
    AssembleEvidencePackRequest,
    GetEvidencePackRequest,
    GetScoreBreakdownRequest,
    SearchEvidenceCandidatesRequest,
)
from evidence_retrieval.composition import EvidenceRetrievalContainer
from evidence_retrieval.domain.values import RecencyPolicy
from evidence_retrieval.interfaces.http.deps import (
    evidence_retrieval_unit_of_work,
    get_container,
)
from evidence_retrieval.interfaces.http.schemas import (
    AssemblePackBody,
    EvidencePackResponse,
    ReweightPackBody,
    ScoreBreakdownResponse,
    SearchCandidatesBody,
    SearchCandidatesResponse,
)
from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["evidence-retrieval"],
    dependencies=[
        Depends(require_declared_scope),
        Depends(evidence_retrieval_unit_of_work),
    ],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)


@router.post(
    "/evidence/candidates",
    status_code=status.HTTP_200_OK,
    response_model=SearchCandidatesResponse,
    summary="Search scored evidence candidates for a claim",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def search_evidence_candidates(
    body: SearchCandidatesBody,
    container: Annotated[EvidenceRetrievalContainer, Depends(get_container)],
) -> SearchCandidatesResponse:
    """Return candidates with stance, score components and provenance."""
    result = await container.search_candidates.execute(
        SearchEvidenceCandidatesRequest(
            claim=body.claim,
            claim_type=body.claim_type,
            snapshot_id=body.snapshot_id,
            limit=body.limit,
        )
    )
    return SearchCandidatesResponse.model_validate(result, from_attributes=True)


@router.post(
    "/evidence/packs",
    status_code=status.HTTP_201_CREATED,
    response_model=EvidencePackResponse,
    summary="Assemble and freeze a balanced evidence pack",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def assemble_evidence_pack(
    body: AssemblePackBody,
    container: Annotated[EvidenceRetrievalContainer, Depends(get_container)],
) -> EvidencePackResponse:
    """Search both directions, record truthful absence, and freeze the pack."""
    result = await container.assemble_pack.execute(
        AssembleEvidencePackRequest(
            claim=body.claim,
            claim_type=body.claim_type,
            snapshot_id=body.snapshot_id,
        )
    )
    return EvidencePackResponse.model_validate(result, from_attributes=True)


@router.get(
    "/evidence/packs/{pack_id}",
    response_model=EvidencePackResponse,
    summary="Read a frozen evidence pack",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_evidence_pack(
    pack_id: str,
    container: Annotated[EvidenceRetrievalContainer, Depends(get_container)],
) -> EvidencePackResponse:
    """Return the pack, its candidates, absence and trace."""
    result = await container.get_pack.execute(GetEvidencePackRequest(pack_id=pack_id))
    return EvidencePackResponse.model_validate(result, from_attributes=True)


@router.get(
    "/evidence/packs/{pack_id}/scores",
    response_model=ScoreBreakdownResponse,
    summary="Inspect per-candidate score components",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_score_breakdown(
    pack_id: str,
    container: Annotated[EvidenceRetrievalContainer, Depends(get_container)],
) -> ScoreBreakdownResponse:
    """Return every candidate's inspectable weight breakdown."""
    result = await container.get_score_breakdown.execute(GetScoreBreakdownRequest(pack_id=pack_id))
    return ScoreBreakdownResponse.model_validate(result, from_attributes=True)


@router.post(
    "/evidence/packs/{pack_id}/reweight",
    status_code=status.HTTP_201_CREATED,
    response_model=EvidencePackResponse,
    summary="Re-score a pack under a new recency policy",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def apply_recency_policy(
    pack_id: str,
    body: ReweightPackBody,
    container: Annotated[EvidenceRetrievalContainer, Depends(get_container)],
) -> EvidencePackResponse:
    """Return a new pack version; the previous version stays immutable."""
    policy = RecencyPolicy(
        half_life_days=body.policy.half_life_days,
        exempt_source_types=frozenset(body.policy.exempt_source_types),
    )
    result = await container.reweight_pack.execute(
        ApplyRecencyPolicyRequest(pack_id=pack_id, policy=policy)
    )
    return EvidencePackResponse.model_validate(result, from_attributes=True)
