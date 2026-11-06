"""DecisionBrief HTTP router — the frozen API surface (ADR-004, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (API Endpoints)

Routes, scopes, payload shapes and error envelopes are the contract. Every handler delegates to a
use case in the container; mounting happens in the wiring issue. Keeping the router concrete here
(no separate handler interface) is deliberate — controllers are not interfaces.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from decision_brief.interfaces.http.schemas import (
    BriefResponse,
    BriefVersionListResponse,
    CitationListResponse,
    VersionBriefBody,
    VersionBriefResponse,
)
from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["decision-brief"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)

_IMPLEMENTED_BY = "decision-brief HTTP surface is implemented by issue-decision-brief-wiring"


@router.post(
    "/runs/{run_id}/brief",
    response_model=BriefResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publish the brief of a closed run",
    openapi_extra={"x-required-scope": "briefs:publish"},
    responses=WRITE_ERRORS,
)
async def publish_decision_brief(run_id: str) -> BriefResponse:
    """Build all eight sections, run every gate, freeze version N and return it."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.get(
    "/briefs/{brief_id}",
    response_model=BriefResponse,
    summary="Read one frozen brief",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_decision_brief(brief_id: str) -> BriefResponse:
    """Return the frozen artefact; the read never re-derives sections."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.get(
    "/runs/{run_id}/briefs",
    response_model=BriefVersionListResponse,
    summary="List every brief version of one run with lineage",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_brief_versions(run_id: str) -> BriefVersionListResponse:
    """Return versions ordered by version number; superseded versions stay retrievable."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.post(
    "/briefs/{brief_id}:version",
    response_model=VersionBriefResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a successor version of a published brief",
    openapi_extra={"x-required-scope": "briefs:publish"},
    responses=WRITE_ERRORS,
)
async def version_decision_brief(brief_id: str, body: VersionBriefBody) -> VersionBriefResponse:
    """Produce version N+1 referencing N and the stated reason; N is unchanged."""
    raise NotImplementedError(_IMPLEMENTED_BY)


@router.get(
    "/briefs/{brief_id}/citations",
    response_model=CitationListResponse,
    summary="Read the citation state of one brief",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_citations(brief_id: str, section: str | None = None) -> CitationListResponse:
    """Return every citation with its resolution state, optionally filtered by section kind."""
    raise NotImplementedError(_IMPLEMENTED_BY)
