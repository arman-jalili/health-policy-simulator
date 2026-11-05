"""Composition root of the EvidenceCorpus context.

Canonical: .pi/architecture/modules/evidence-corpus.md

One place where ports and adapters are wired. The adapter family is selected from
``Settings.persistence`` (ADR-002): PostgreSQL is the default, in-memory is explicit and reserved
for tests plus a database-less local demo. Nothing in the domain or application layer knows which
family is active.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from evidence_corpus.application.authority_handler import ClassifySourceAuthorityHandler
from evidence_corpus.application.authority_read_handlers import ListAuthorityRulesHandler
from evidence_corpus.application.canonical_handler import LinkCanonicalArticleHandler
from evidence_corpus.application.events import EventPublisher
from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
from evidence_corpus.application.indexing_handler import IndexIngestedPassagesHandler
from evidence_corpus.application.ingestion_handlers import (
    GetIngestionRunHandler,
    IngestDocumentHandler,
    StartIngestionRunHandler,
)
from evidence_corpus.application.ports import IndexWriterPort
from evidence_corpus.application.read_handlers import GetDocumentHandler, ResolvePassageHandler
from evidence_corpus.application.segmentation_handler import SegmentArticleHandler
from evidence_corpus.application.snapshot_handlers import (
    GetCorpusSnapshotHandler,
    PinCorpusSnapshotHandler,
)
from evidence_corpus.domain.repositories import (
    ArticleRepository,
    AuthorityRuleRepository,
    CorpusSnapshotRepository,
    DocumentRepository,
    IngestionRunRepository,
    PassageRepository,
)
from evidence_corpus.infrastructure.events import OutboxEventPublisher
from evidence_corpus.infrastructure.extraction.ocr import TesseractOcrExtractor
from evidence_corpus.infrastructure.extraction.pymupdf import PyMuPdfExtractor
from evidence_corpus.infrastructure.indexing.memory import InMemoryIndexWriter
from evidence_corpus.infrastructure.indexing.postgres import PostgresIndexWriter
from evidence_corpus.infrastructure.logging_events import LoggingEventPublisher
from evidence_corpus.infrastructure.memory import (
    InMemoryArticleRepository,
    InMemoryAuthorityRuleRepository,
    InMemoryCorpusSnapshotRepository,
    InMemoryDocumentRepository,
    InMemoryIngestionRunRepository,
    InMemoryPassageRepository,
)
from evidence_corpus.infrastructure.repository.sqlalchemy import (
    SqlAlchemyArticleRepository,
    SqlAlchemyAuthorityRuleRepository,
    SqlAlchemyCorpusSnapshotRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionRunRepository,
    SqlAlchemyPassageRepository,
)
from shared.config import Settings, get_settings
from shared.db import Database, UnitOfWork
from shared.enums import Persistence


@dataclass
class CorpusContainer:
    """Wired use cases and their adapters for one application process."""

    documents: DocumentRepository
    articles: ArticleRepository
    passages: PassageRepository
    ingestion_runs: IngestionRunRepository
    snapshots: CorpusSnapshotRepository
    authority_rules: AuthorityRuleRepository
    events: EventPublisher

    extract_document_text: ExtractDocumentTextHandler
    classify_source_authority: ClassifySourceAuthorityHandler
    link_canonical_article: LinkCanonicalArticleHandler
    pin_corpus_snapshot: PinCorpusSnapshotHandler
    get_corpus_snapshot: GetCorpusSnapshotHandler
    index_ingested_passages: IndexIngestedPassagesHandler
    index_writer: IndexWriterPort
    ingest_document: IngestDocumentHandler
    start_ingestion_run: StartIngestionRunHandler
    get_ingestion_run: GetIngestionRunHandler
    list_authority_rules: ListAuthorityRulesHandler
    segment_article: SegmentArticleHandler
    resolve_passage: ResolvePassageHandler
    get_document: GetDocumentHandler
    unit_of_work: UnitOfWork | None = None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Run one logical use case in a single transaction (no-op for in-memory)."""
        if self.unit_of_work is None:
            yield
            return
        async with self.unit_of_work.transaction():
            yield


def build_container(
    settings: Settings | None = None,
    database: Database | None = None,
    actor: str = "system",
) -> CorpusContainer:
    """Wire the corpus for the configured persistence family."""
    app_settings = settings or get_settings()
    if app_settings.persistence is Persistence.MEMORY:
        return _build_memory_container(actor=actor)
    if database is None:
        raise ValueError(
            "PERSISTENCE=postgres requires a Database; the application shell owns the engine"
        )
    return _build_postgres_container(database, actor=actor)


def _build_memory_container(actor: str) -> CorpusContainer:
    """Database-less adapters for unit tests and an explicit local demo."""
    documents = InMemoryDocumentRepository()
    articles = InMemoryArticleRepository(documents)
    passages = InMemoryPassageRepository(documents)
    ingestion_runs = InMemoryIngestionRunRepository()
    snapshots = InMemoryCorpusSnapshotRepository()
    authority_rules = InMemoryAuthorityRuleRepository()
    events = LoggingEventPublisher()
    index_writer = InMemoryIndexWriter()
    return _wire(
        documents=documents,
        articles=articles,
        passages=passages,
        ingestion_runs=ingestion_runs,
        snapshots=snapshots,
        authority_rules=authority_rules,
        events=events,
        index_writer=index_writer,
        actor=actor,
    )


def _build_postgres_container(database: Database, actor: str) -> CorpusContainer:
    """PostgreSQL adapters sharing one unit of work with the outbox publisher."""
    unit_of_work = UnitOfWork(database.session_factory)
    return _wire(
        documents=SqlAlchemyDocumentRepository(unit_of_work),
        articles=SqlAlchemyArticleRepository(unit_of_work),
        passages=SqlAlchemyPassageRepository(unit_of_work),
        ingestion_runs=SqlAlchemyIngestionRunRepository(unit_of_work),
        snapshots=SqlAlchemyCorpusSnapshotRepository(unit_of_work),
        authority_rules=SqlAlchemyAuthorityRuleRepository(unit_of_work),
        events=OutboxEventPublisher(unit_of_work),
        index_writer=PostgresIndexWriter(database.session_factory),
        actor=actor,
        unit_of_work=unit_of_work,
    )


def _wire(
    *,
    documents: DocumentRepository,
    articles: ArticleRepository,
    passages: PassageRepository,
    ingestion_runs: IngestionRunRepository,
    snapshots: CorpusSnapshotRepository,
    authority_rules: AuthorityRuleRepository,
    events: EventPublisher,
    index_writer: IndexWriterPort,
    actor: str,
    unit_of_work: UnitOfWork | None = None,
) -> CorpusContainer:
    extract_handler = ExtractDocumentTextHandler(
        documents, PyMuPdfExtractor(), TesseractOcrExtractor(), events, actor=actor
    )
    return CorpusContainer(
        documents=documents,
        articles=articles,
        passages=passages,
        ingestion_runs=ingestion_runs,
        snapshots=snapshots,
        authority_rules=authority_rules,
        events=events,
        extract_document_text=extract_handler,
        classify_source_authority=ClassifySourceAuthorityHandler(
            documents, articles, events, actor=actor
        ),
        link_canonical_article=LinkCanonicalArticleHandler(articles, events, actor=actor),
        index_ingested_passages=IndexIngestedPassagesHandler(
            documents, index_writer, events, actor=actor
        ),
        index_writer=index_writer,
        ingest_document=IngestDocumentHandler(documents, extract_handler),
        start_ingestion_run=StartIngestionRunHandler(ingestion_runs),
        get_ingestion_run=GetIngestionRunHandler(ingestion_runs),
        list_authority_rules=ListAuthorityRulesHandler(authority_rules),
        pin_corpus_snapshot=PinCorpusSnapshotHandler(documents, snapshots, events, actor=actor),
        get_corpus_snapshot=GetCorpusSnapshotHandler(snapshots),
        segment_article=SegmentArticleHandler(documents, events, actor=actor),
        resolve_passage=ResolvePassageHandler(passages),
        get_document=GetDocumentHandler(documents),
        unit_of_work=unit_of_work,
    )
