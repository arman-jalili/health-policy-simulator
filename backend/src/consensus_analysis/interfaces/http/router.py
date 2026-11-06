"""ConsensusAnalysis HTTP router — the frozen API surface (ADR-004, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (API Endpoints)

Routes, scopes, payload shapes and error envelopes are the contract. Every handler delegates to a
use case in the container; mounting happens in the wiring issue. Keeping the router concrete here
(no separate handler interface) is deliberate — controllers are not interfaces.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from consensus_analysis.interfaces.http.schemas import (
    AssessImpactBody,
    AssessImpactResponse,
    ComparisonResponse,
    ComposePackageBody,
    ComposePackageResponse,
    ConsensusResponse,
    DeriveBody,
    PackageListResponse,
    UnresolvedConflictListResponse,
)
from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["consensus-analysis"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)

_IMPLEMENTED_BY = "consensus-analysis HTTP surface is implemented by issue #320"


@router.post(
    "/runs/{run_id}/analysis:derive",
    response_model=ConsensusResponse,
    summary="Derive the consensus records of a closed run",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def derive_consensus(run_id: str, body: DeriveBody) -> ConsensusResponse:
    """Derive every topic outcome from the closed run log; never assume agreement."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.get(
    "/runs/{run_id}/consensus",
    response_model=ConsensusResponse,
    summary="Read the derived consensus records with majority and minority",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_consensus(run_id: str) -> ConsensusResponse:
    """Return the persisted projection; the read never recomputes the outcome."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.get(
    "/runs/{run_id}/conflicts/open",
    response_model=UnresolvedConflictListResponse,
    summary="List the conflicts still open at run close",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_unresolved_conflicts(run_id: str) -> UnresolvedConflictListResponse:
    """Return every unresolved conflict together with the positions that remain apart."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.post(
    "/runs/{run_id}/packages",
    response_model=ComposePackageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compose a compromise package from accepted components",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def compose_compromise_package(
    run_id: str, body: ComposePackageBody
) -> ComposePackageResponse:
    """Combine individually accepted, compatible components and document every rejection."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.get(
    "/runs/{run_id}/packages",
    response_model=PackageListResponse,
    summary="List composed packages with their provenance counters",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_packages(run_id: str) -> PackageListResponse:
    """Return the packages of one run with accepted and rejected counts."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.post(
    "/packages/{package_id}/scenarios",
    response_model=AssessImpactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Define and assess a scenario against a package",
    openapi_extra={"x-required-scope": "runs:write"},
    responses=WRITE_ERRORS,
)
async def assess_impact(package_id: str, body: AssessImpactBody) -> AssessImpactResponse:
    """Estimate the impacts, refusing any figure that cannot prove its basis."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.get(
    "/packages/{package_id}/comparison",
    response_model=ComparisonResponse,
    summary="Rank alternative packages on cost, acceptance and feasibility",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def compare_scenarios(package_id: str) -> ComparisonResponse:
    """Return ranked alternatives; a comparison missing a dimension is invalid."""
    raise NotImplementedError(_IMPLEMENTED_BY)
