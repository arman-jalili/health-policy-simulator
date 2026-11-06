"""DecisionBrief HTTP router — the frozen API surface (ADR-004, issue #331).

Canonical: ``.pi/architecture/modules/decision-brief.md`` (API Endpoints)

Routes, scopes, payload shapes and error envelopes are the contract. Every handler delegates to a
use case in the container; mounting happens in the wiring issue. Keeping the router concrete here
(no separate handler interface) is deliberate — controllers are not interfaces.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from decision_brief.application.commands import (
    GetDecisionBriefRequest,
    ListBriefVersionsRequest,
    ListCitationsRequest,
    PublishDecisionBriefRequest,
    VersionDecisionBriefRequest,
)
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.values import BriefId, CitationReference, RunId, SectionKind
from decision_brief.interfaces.http.deps import DecisionBriefContainer, get_container
from decision_brief.interfaces.http.schemas import (
    BriefResponse,
    BriefVersionListResponse,
    BriefVersionSummary,
    CitationBody,
    CitationListResponse,
    VersionBriefBody,
    VersionBriefResponse,
)
from decision_brief.interfaces.renderer import brief_document
from identity_access.interfaces.http.dependencies import require_declared_scope
from shared.http.schemas import error_responses

router = APIRouter(
    prefix="/api/v1",
    tags=["decision-brief"],
    dependencies=[Depends(require_declared_scope)],
)

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 404, 409, 422, 503)

Container = Annotated[DecisionBriefContainer, Depends(get_container)]


def _brief_response(brief: DecisionBrief) -> BriefResponse:
    """One mapping for every route: the renderer's document, validated by the frozen schema."""
    return BriefResponse.model_validate(brief_document(brief))


def _citation_body(citation: CitationReference) -> CitationBody:
    provenance = citation.provenance
    return CitationBody(
        passage_id=str(citation.passage_id),
        resolved=citation.is_resolved(),
        quote=citation.quote,
        outlet=provenance.outlet if provenance is not None else None,
        published_on=provenance.published_on if provenance is not None else None,
        medium=provenance.medium if provenance is not None else None,
        page_from=provenance.page_from if provenance is not None else None,
        page_to=provenance.page_to if provenance is not None else None,
        source_uri=provenance.source_uri if provenance is not None else None,
    )


@router.post(
    "/runs/{run_id}/brief",
    response_model=BriefResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publish the brief of a closed run",
    openapi_extra={"x-required-scope": "briefs:publish"},
    responses=WRITE_ERRORS,
)
async def publish_decision_brief(run_id: str, container: Container) -> BriefResponse:
    """Build all eight sections, run every gate, freeze version N and return it."""
    result = await container.publish_decision_brief.execute(
        PublishDecisionBriefRequest(run_id=RunId(run_id))
    )
    return _brief_response(result.brief)


@router.get(
    "/briefs/{brief_id}",
    response_model=BriefResponse,
    summary="Read one frozen brief",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def get_decision_brief(brief_id: str, container: Container) -> BriefResponse:
    """Return the frozen artefact; the read never re-derives sections."""
    result = await container.get_decision_brief.execute(
        GetDecisionBriefRequest(brief_id=BriefId(brief_id))
    )
    return _brief_response(result.brief)


@router.get(
    "/runs/{run_id}/briefs",
    response_model=BriefVersionListResponse,
    summary="List every brief version of one run with lineage",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_brief_versions(run_id: str, container: Container) -> BriefVersionListResponse:
    """Return versions ordered by version number; superseded versions stay retrievable."""
    result = await container.list_brief_versions.execute(
        ListBriefVersionsRequest(run_id=RunId(run_id))
    )
    return BriefVersionListResponse(
        run_id=run_id,
        versions=[
            BriefVersionSummary(
                brief_id=str(item.brief.id),
                version=item.brief.version.number,
                previous_version=item.brief.version.previous_version,
                reason=item.brief.version.reason,
                status=item.brief.status.value,
                generated_at=item.brief.version.generated_at,
            )
            for item in result.items
        ],
    )


@router.post(
    "/briefs/{brief_id}:version",
    response_model=VersionBriefResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a successor version of a published brief",
    openapi_extra={"x-required-scope": "briefs:publish"},
    responses=WRITE_ERRORS,
)
async def version_decision_brief(
    brief_id: str, body: VersionBriefBody, container: Container
) -> VersionBriefResponse:
    """Produce version N+1 referencing N and the stated reason; N is unchanged."""
    result = await container.version_decision_brief.execute(
        VersionDecisionBriefRequest(brief_id=BriefId(brief_id), reason=body.reason)
    )
    version = result.brief.version
    return VersionBriefResponse(
        brief_id=str(result.brief.id),
        previous_version=version.previous_version or 1,
        version=version.number,
        reason=body.reason,
    )


@router.get(
    "/briefs/{brief_id}/citations",
    response_model=CitationListResponse,
    summary="Read the citation state of one brief",
    openapi_extra={"x-required-scope": "runs:read"},
    responses=READ_ERRORS,
)
async def list_citations(
    brief_id: str,
    container: Container,
    section: str | None = Query(default=None),
) -> CitationListResponse:
    """Return every citation with its resolution state, optionally filtered by section kind."""
    result = await container.list_citations.execute(
        ListCitationsRequest(
            brief_id=BriefId(brief_id),
            section=SectionKind(section) if section is not None else None,
        )
    )
    return CitationListResponse(
        brief_id=brief_id,
        section=result.section.value if result.section is not None else None,
        items=[_citation_body(citation) for citation in result.citations],
    )
