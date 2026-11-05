"""EvidenceCorpus HTTP router — the frozen API surface (ADR-004).

Canonical: .pi/architecture/modules/evidence-corpus.md

The routes, their scopes, payload shapes and error envelopes are the contract. Handlers are not
wired yet: they answer `501 ENDPOINT_NOT_IMPLEMENTED` with the standard envelope, so a caller can
already integrate against the contract without mistaking a stub for working ingestion.

Required scopes are declared as `x-required-scope` in the OpenAPI document; Phase 1 IdentityAccess
supplies the `require_scope` dependency that enforces them at runtime (ADR-005).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from evidence_corpus.application.commands import (
    GetCorpusSnapshotRequest,
    GetDocumentRequest,
    PinCorpusSnapshotRequest,
    ResolvePassageRequest,
)
from evidence_corpus.composition import CorpusContainer
from evidence_corpus.domain.values import ClaimType
from evidence_corpus.interfaces.http.deps import get_container
from evidence_corpus.interfaces.http.schemas import (
    AuthorityRuleResponse,
    DocumentIngestionBody,
    DocumentResponse,
    IngestDocumentBody,
    IngestionRunResponse,
    PassageResponse,
    PinSnapshotBody,
    PinSnapshotResponse,
    SnapshotResponse,
    StartIngestionRunBody,
    StartIngestionRunResponse,
)
from shared.errors import EndpointNotImplementedError
from shared.http.schemas import error_responses

router = APIRouter(prefix="/api/v1", tags=["corpus"])

READ_ERRORS = error_responses(401, 403, 404, 503)
WRITE_ERRORS = error_responses(401, 403, 409, 422, 503)


def _not_implemented(operation: str) -> EndpointNotImplementedError:
    return EndpointNotImplementedError(
        f"{operation} is part of the frozen EvidenceCorpus contract and not implemented yet"
    )


@router.post(
    "/corpus/documents",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentIngestionBody,
    summary="Register and extract a source document",
    openapi_extra={"x-required-scope": "corpus:write"},
    responses=WRITE_ERRORS,
)
async def ingest_document(body: IngestDocumentBody) -> DocumentIngestionBody:
    """Ingest a source file; the response reports measured quality and citability."""
    raise _not_implemented("POST /api/v1/corpus/documents")


@router.post(
    "/corpus/ingestion-runs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StartIngestionRunResponse,
    summary="Start an auditable ingestion batch",
    openapi_extra={"x-required-scope": "corpus:write"},
    responses=WRITE_ERRORS,
)
async def start_ingestion_run(body: StartIngestionRunBody) -> StartIngestionRunResponse:
    """Open a batch run over a shard of source paths; work proceeds on a worker."""
    raise _not_implemented("POST /api/v1/corpus/ingestion-runs")


@router.get(
    "/corpus/ingestion-runs/{run_id}",
    response_model=IngestionRunResponse,
    summary="Read ingestion run progress and outcome counts",
    openapi_extra={"x-required-scope": "corpus:read"},
    responses=READ_ERRORS,
)
async def get_ingestion_run(
    run_id: Annotated[str, Path(description="Prefixed ULID of the ingestion run")],
) -> IngestionRunResponse:
    """Return attempted/accepted/quarantined/failed counts and the run status."""
    raise _not_implemented("GET /api/v1/corpus/ingestion-runs/{run_id}")


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Read a document with its articles",
    openapi_extra={"x-required-scope": "corpus:read"},
    responses=READ_ERRORS,
)
async def get_document(
    document_id: Annotated[str, Path(description="Prefixed ULID of the document")],
    container: Annotated[CorpusContainer, Depends(get_container)],
) -> DocumentResponse:
    """Return publication, extraction quality, authority tier and segmented articles."""
    view = await container.get_document.execute(GetDocumentRequest(document_id=document_id))
    return DocumentResponse.model_validate(view, from_attributes=True)


@router.get(
    "/passages/{passage_id}",
    response_model=PassageResponse,
    summary="Resolve a citation to text plus provenance",
    openapi_extra={"x-required-scope": "corpus:read"},
    responses=READ_ERRORS,
)
async def get_passage(
    passage_id: Annotated[str, Path(description="Prefixed ULID of the passage")],
    container: Annotated[CorpusContainer, Depends(get_container)],
) -> PassageResponse:
    """Return text, offsets, page and outlet so the reader can verify the source slice."""
    view = await container.resolve_passage.execute(ResolvePassageRequest(passage_id=passage_id))
    return PassageResponse.model_validate(view, from_attributes=True)


@router.post(
    "/corpus/snapshots",
    status_code=status.HTTP_201_CREATED,
    response_model=PinSnapshotResponse,
    summary="Pin a corpus snapshot",
    openapi_extra={"x-required-scope": "corpus:write"},
    responses=WRITE_ERRORS,
)
async def pin_corpus_snapshot(
    body: PinSnapshotBody,
    container: Annotated[CorpusContainer, Depends(get_container)],
) -> PinSnapshotResponse:
    """Freeze the document set and index version a later run may search."""
    view = await container.pin_corpus_snapshot.execute(
        PinCorpusSnapshotRequest(label=body.label, document_ids=body.document_ids)
    )
    return PinSnapshotResponse(snapshot_id=view.snapshot_id, manifest_hash=view.manifest_hash)


@router.get(
    "/corpus/snapshots/{snapshot_id}",
    response_model=SnapshotResponse,
    summary="Read a snapshot manifest and its index version",
    openapi_extra={"x-required-scope": "corpus:read"},
    responses=READ_ERRORS,
)
async def get_snapshot(
    snapshot_id: Annotated[str, Path(description="Prefixed ULID of the snapshot")],
    container: Annotated[CorpusContainer, Depends(get_container)],
) -> SnapshotResponse:
    """Return the pinned document set plus the index manifest consumers must quote."""
    view = await container.get_corpus_snapshot.execute(
        GetCorpusSnapshotRequest(snapshot_id=snapshot_id)
    )
    return SnapshotResponse.model_validate(view, from_attributes=True)


@router.get(
    "/corpus/authority-rules",
    response_model=list[AuthorityRuleResponse],
    summary="List the authority rubric per claim type",
    openapi_extra={"x-required-scope": "corpus:read"},
    responses=READ_ERRORS,
)
async def list_authority_rules(
    claim_type: Annotated[
        ClaimType | None,
        Query(description="Restrict to one claim type; omitted returns every rule"),
    ] = None,
) -> list[AuthorityRuleResponse]:
    """Return the frozen tier ordering; authority is claim-type relative, never global."""
    raise _not_implemented("GET /api/v1/corpus/authority-rules")
