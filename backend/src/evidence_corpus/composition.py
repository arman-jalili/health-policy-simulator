"""Composition root of the EvidenceCorpus context.

Canonical: .pi/architecture/modules/evidence-corpus.md

One place where ports and adapters are wired. Persistence starts in memory (the SQLAlchemy adapters
are added by the persistence issues); swapping them happens here only.
"""

from __future__ import annotations

from dataclasses import dataclass

from evidence_corpus.application.authority_handler import ClassifySourceAuthorityHandler
from evidence_corpus.application.canonical_handler import LinkCanonicalArticleHandler
from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
from evidence_corpus.application.indexing_handler import IndexIngestedPassagesHandler
from evidence_corpus.application.read_handlers import GetDocumentHandler, ResolvePassageHandler
from evidence_corpus.application.segmentation_handler import SegmentArticleHandler
from evidence_corpus.application.snapshot_handlers import (
    GetCorpusSnapshotHandler,
    PinCorpusSnapshotHandler,
)
from evidence_corpus.infrastructure.extraction.ocr import TesseractOcrExtractor
from evidence_corpus.infrastructure.extraction.pymupdf import PyMuPdfExtractor
from evidence_corpus.infrastructure.indexing.memory import InMemoryIndexWriter
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
    classify_source_authority: ClassifySourceAuthorityHandler
    link_canonical_article: LinkCanonicalArticleHandler
    pin_corpus_snapshot: PinCorpusSnapshotHandler
    get_corpus_snapshot: GetCorpusSnapshotHandler
    index_ingested_passages: IndexIngestedPassagesHandler
    index_writer: InMemoryIndexWriter
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
    index_writer = InMemoryIndexWriter()

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
        classify_source_authority=ClassifySourceAuthorityHandler(
            documents, articles, events, actor=actor
        ),
        link_canonical_article=LinkCanonicalArticleHandler(articles, events, actor=actor),
        index_ingested_passages=IndexIngestedPassagesHandler(
            documents, index_writer, events, actor=actor
        ),
        index_writer=index_writer,
        pin_corpus_snapshot=PinCorpusSnapshotHandler(documents, snapshots, events),
        get_corpus_snapshot=GetCorpusSnapshotHandler(snapshots),
        segment_article=SegmentArticleHandler(documents, events, actor=actor),
        resolve_passage=ResolvePassageHandler(passages),
        get_document=GetDocumentHandler(documents),
    )
