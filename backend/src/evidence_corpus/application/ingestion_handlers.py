"""Ingestion use cases: register a source file and run an auditable batch.

Canonical: .pi/architecture/modules/evidence-corpus.md

`IngestDocument` registers the file, extracts it through the extraction use case and reports the
measured quality. `StartIngestionRun` opens the batch record; the worker processes shards and calls
`IngestionRun.record` per document.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from evidence_corpus.application.commands import (
    ExtractDocumentTextRequest,
    GetIngestionRunRequest,
    IndexIngestedPassagesRequest,
    IngestDocumentRequest,
    PublicationInput,
    SegmentArticleRequest,
    StartIngestionRunRequest,
)
from evidence_corpus.application.dto import (
    DocumentIngestionResult,
    ExtractionOutcome,
    IngestionRunView,
)
from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
from evidence_corpus.application.indexing_handler import IndexIngestedPassagesHandler
from evidence_corpus.application.segmentation_handler import SegmentArticleHandler
from evidence_corpus.domain.entities import Document, IngestionOutcome, IngestionRun, Publication
from evidence_corpus.domain.errors import OcrUnavailable, RunNotFound
from evidence_corpus.domain.repositories import DocumentRepository, IngestionRunRepository
from evidence_corpus.domain.values import LANGUAGE_DE_AT, LanguageTag, SourceType
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

        if existing is not None and existing.quality is not None:
            # Re-running a shard is idempotent: the extraction is immutable, so reuse it instead
            # of raising `AlreadyExtracted` and turning a resume into a failed path.
            outcome = ExtractionOutcome(
                document_id=document.id,
                text=existing.extracted_text or "",
                quality=existing.quality,
            )
        else:
            outcome = await self._extraction.execute(
                ExtractDocumentTextRequest(document_id=document.id)
            )
        # Extraction saves through its own repository read, so the local instance may still hold
        # the pre-extraction state. Re-read the aggregate instead of aliasing repository internals.
        reloaded = await self._documents.get(document.id)
        return DocumentIngestionResult(
            document_id=document.id,
            quality=outcome.quality,
            # "citable" means a publishable passage exists, not merely acceptable extraction.
            citable=bool(reloaded.publishable_passages()) if reloaded is not None else False,
        )


class StartIngestionRunHandler:
    """Implements :class:`evidence_corpus.application.services.StartIngestionRun`.

    When the pipeline handlers are available the batch is executed document by document; without
    them it is a register-only row. Either way the returned status says which happened.
    """

    def __init__(
        self,
        runs: IngestionRunRepository,
        *,
        ingest: IngestDocumentHandler | None = None,
        segment: SegmentArticleHandler | None = None,
        index: IndexIngestedPassagesHandler | None = None,
    ) -> None:
        self._runs = runs
        self._ingest = ingest
        self._segment = segment
        self._index = index

    async def execute(self, request: StartIngestionRunRequest) -> IngestionRunView:
        run = IngestionRun(id=new_id("run"), shard_label=request.shard_label)
        if self._ingest is None or self._segment is None or self._index is None:
            await self._runs.save(run)
            return ingestion_run_view(run)
        for path in request.paths:
            try:
                ingested = await self._ingest.execute(
                    IngestDocumentRequest(
                        source_uri=path,
                        publication=PublicationInput(
                            outlet="batch", published_on=date.today(), medium="online"
                        ),
                        source_type=SourceType.PRESS_REPORT,
                    )
                )
                await self._segment.execute(SegmentArticleRequest(document_id=ingested.document_id))
                manifest = await self._index.execute(
                    IndexIngestedPassagesRequest(document_id=ingested.document_id)
                )
                if manifest.passage_count > 0:
                    run.record(IngestionOutcome.ACCEPTED, path=path)
                else:
                    run.record(
                        IngestionOutcome.QUARANTINED,
                        path=path,
                        reason="no citable passages after extraction/segmentation",
                    )
            except OcrUnavailable as error:
                run.record(
                    IngestionOutcome.FAILED,
                    path=path,
                    reason=f"{error.code}: {error.message}",
                )
            except Exception as error:
                run.record(
                    IngestionOutcome.FAILED,
                    path=path,
                    reason=f"{type(error).__name__}: {error}",
                )
        if (
            run.attempted
            and run.failed == run.attempted
            and all((item.reason or "").startswith(OcrUnavailable.code) for item in run.outcomes)
        ):
            run.fail("OCR_UNAVAILABLE: the batch needs tesseract, but the OCR stack is absent")
        else:
            run.complete()
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
        status=run.status.value,
        attempted=run.attempted,
        accepted=run.accepted,
        quarantined=run.quarantined,
        failed=run.failed,
        outcomes=tuple(run.outcomes),
        failure_reason=run.failure_reason,
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
