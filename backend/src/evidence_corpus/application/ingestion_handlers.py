"""Ingestion use cases: register a source file and run an auditable batch.

Canonical: .pi/architecture/modules/evidence-corpus.md

`IngestDocument` registers the file, extracts it through the extraction use case and reports the
measured quality. `StartIngestionRun` opens the batch record; the worker processes shards and calls
`IngestionRun.record` per document.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from evidence_corpus.application.commands import (
    ExtractDocumentTextRequest,
    GetIngestionRunRequest,
    IngestDocumentRequest,
    StartIngestionRunRequest,
)
from evidence_corpus.application.dto import DocumentIngestionResult, IngestionRunView
from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
from evidence_corpus.domain.entities import Document, IngestionRun, Publication
from evidence_corpus.domain.errors import RunNotFound
from evidence_corpus.domain.repositories import DocumentRepository, IngestionRunRepository
from evidence_corpus.domain.values import LANGUAGE_DE_AT, LanguageTag
from shared.ids import new_id


class IngestDocumentHandler:
    """Implements :class:`evidence_corpus.application.services.IngestDocument`."""

    def __init__(
        self,
        documents: DocumentRepository,
        extraction: ExtractDocumentTextHandler,
    ) -> None:
        self._documents = documents
        self._extraction = extraction

    async def execute(self, request: IngestDocumentRequest) -> DocumentIngestionResult:
        content_hash = _content_hash(request.source_uri)
        existing = await self._documents.get_by_hash(content_hash)
        if existing is None:
            document = Document.register(
                source_uri=request.source_uri,
                content_hash=content_hash,
                publication=Publication(
                    outlet=request.publication.outlet,
                    published_on=request.publication.published_on,
                    medium=request.publication.medium,
                ),
                source_type=request.source_type,
                language=_language_of(request.source_uri),
            )
            await self._documents.save(document)
        else:
            document = existing

        outcome = await self._extraction.execute(
            ExtractDocumentTextRequest(document_id=document.id)
        )
        return DocumentIngestionResult(
            document_id=document.id,
            quality=outcome.quality,
            citable=document.is_citable(),
        )


class StartIngestionRunHandler:
    """Implements :class:`evidence_corpus.application.services.StartIngestionRun`."""

    def __init__(self, runs: IngestionRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: StartIngestionRunRequest) -> IngestionRunView:
        run = IngestionRun(id=new_id("run"), shard_label=request.shard_label)
        await self._runs.save(run)
        return ingestion_run_view(run)


class GetIngestionRunHandler:
    """Implements :class:`evidence_corpus.application.services.GetIngestionRun`."""

    def __init__(self, runs: IngestionRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: GetIngestionRunRequest) -> IngestionRunView:
        run_id = request.run_id
        run = await self._runs.get(run_id)
        if run is None:
            raise RunNotFound(run_id)
        return ingestion_run_view(run)


def ingestion_run_view(run: IngestionRun) -> IngestionRunView:
    return IngestionRunView(
        run_id=run.id,
        shard_label=run.shard_label,
        status=str(run.status),
        attempted=run.attempted,
        accepted=run.accepted,
        quarantined=run.quarantined,
        failed=run.failed,
    )


def _content_hash(source_uri: str) -> str:
    path = Path(source_uri.removeprefix("file://"))
    if "://" not in source_uri and path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return f"sha256:{digest.hexdigest()}"
    return "sha256:" + hashlib.sha256(source_uri.encode("utf-8")).hexdigest()


def _language_of(source_uri: str) -> LanguageTag:
    """Source language is declared by the operator; the prototype corpus is German."""
    return LANGUAGE_DE_AT
