"""Composition root of the EvidenceCorpus context.

Canonical: .pi/architecture/modules/evidence-corpus.md

One place where ports and adapters are wired. Persistence starts in memory (the SQLAlchemy adapters
are added by the persistence issues); swapping them happens here only.
"""

from __future__ import annotations

from dataclasses import dataclass

from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
from evidence_corpus.application.read_handlers import GetDocumentHandler, ResolvePassageHandler
from evidence_corpus.application.segmentation_handler import SegmentArticleHandler
from evidence_corpus.infrastructure.extraction.ocr import TesseractOcrExtractor
from evidence_corpus.infrastructure.extraction.pymupdf import PyMuPdfExtractor
from evidence_corpus.infrastructure.logging_events import LoggingEventPublisher
from evidence_corpus.infrastructure.memory import (
    InMemoryArticleRepository,
    InMemoryAuthorityRuleRepository,
    InMemoryCorpusSnapshotRepository,
    InMemoryDocumentRepository,
    InMemoryIngestionRunRepository,
    InMemoryPassageRepository,
)


@dataclass
class CorpusContainer:
    """Wired use cases and their adapters for one application process."""

    documents: InMemoryDocumentRepository
    articles: InMemoryArticleRepository
    passages: InMemoryPassageRepository
    ingestion_runs: InMemoryIngestionRunRepository
    snapshots: InMemoryCorpusSnapshotRepository
    authority_rules: InMemoryAuthorityRuleRepository
    events: LoggingEventPublisher

    extract_document_text: ExtractDocumentTextHandler
    segment_article: SegmentArticleHandler
    resolve_passage: ResolvePassageHandler
    get_document: GetDocumentHandler


def build_container(actor: str = "system") -> CorpusContainer:
    documents = InMemoryDocumentRepository()
    articles = InMemoryArticleRepository(documents)
    passages = InMemoryPassageRepository(documents)
    ingestion_runs = InMemoryIngestionRunRepository()
    snapshots = InMemoryCorpusSnapshotRepository()
    authority_rules = InMemoryAuthorityRuleRepository()
    events = LoggingEventPublisher()

    return CorpusContainer(
        documents=documents,
        articles=articles,
        passages=passages,
        ingestion_runs=ingestion_runs,
        snapshots=snapshots,
        authority_rules=authority_rules,
        events=events,
        extract_document_text=ExtractDocumentTextHandler(
            documents, PyMuPdfExtractor(), TesseractOcrExtractor(), events, actor=actor
        ),
        segment_article=SegmentArticleHandler(documents, events, actor=actor),
        resolve_passage=ResolvePassageHandler(passages),
        get_document=GetDocumentHandler(documents),
    )
