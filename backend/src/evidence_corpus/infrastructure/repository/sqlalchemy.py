"""SQLAlchemy adapters for the EvidenceCorpus repository ports.

Canonical: .pi/architecture/modules/evidence-corpus.md

Every adapter joins the ambient :class:`shared.db.UnitOfWork` transaction, so an aggregate write
and the events it drained reach the database atomically (ADR-002/ADR-003). ORM models and column
names stay private to this module; callers only see domain entities and published views.

The authority rubric is frozen domain data (``domain.values.AUTHORITY_RULES``), so its adapter reads
code rather than a table: there is deliberately no migration that a rubric row could drift from.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from evidence_corpus.domain.entities import (
    Article,
    CorpusSnapshot,
    Document,
    IndexManifest,
    IngestionRun,
    Passage,
    Publication,
    RunStatus,
)
from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.values import (
    ArticleSection,
    AuthorityRule,
    AuthorityTier,
    ClaimType,
    ExtractionMethod,
    ExtractionQuality,
    LanguageTag,
    Offsets,
    Provenance,
    SourceType,
    SpeakerKind,
    authority_rule,
)
from evidence_corpus.infrastructure.indexing.models import IndexManifestRow
from evidence_corpus.infrastructure.mapping import provenance_view
from evidence_corpus.infrastructure.repository.models import (
    ArticleRow,
    CorpusSnapshotRow,
    DocumentRow,
    IngestionRunRow,
    PassageRow,
    PublicationRow,
    SnapshotDocumentRow,
)
from shared.db import UnitOfWork

_ZERO_INDEX_VERSION = "idx-0"


def article_content_hash(body: str) -> str:
    """Normalised body digest used for duplicate detection (same rule as the use cases)."""
    normalized = " ".join(body.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class SqlAlchemyDocumentRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.DocumentRepository`."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def get(self, document_id: str) -> Document | None:
        statement = (
            select(DocumentRow)
            .options(*_document_loaders())
            .where(DocumentRow.id == document_id)
            .execution_options(populate_existing=True)
        )
        async with self._uow.session() as session:
            row = await session.scalar(statement)
        return _to_document(row) if row is not None else None

    async def get_by_hash(self, content_hash: str) -> Document | None:
        statement = (
            select(DocumentRow)
            .options(*_document_loaders())
            .where(DocumentRow.content_hash == content_hash)
            .limit(1)
            .execution_options(populate_existing=True)
        )
        async with self._uow.session() as session:
            row = await session.scalar(statement)
        return _to_document(row) if row is not None else None

    async def save(self, document: Document) -> None:
        async with self._uow.session() as session:
            row = await session.get(DocumentRow, document.id)
            if row is None:
                row = DocumentRow(id=document.id)
                session.add(row)
            _apply_document(row, document)
            if row.publication is None:
                row.publication = _publication_row(document)
            else:
                _apply_publication(row.publication, document)
            await session.flush()
            await _sync_articles(session, document)

    async def next_documents(self, limit: int) -> list[str]:
        statement = select(DocumentRow.id).order_by(DocumentRow.id).limit(limit)
        async with self._uow.session() as session:
            return list(await session.scalars(statement))

    async def list_by_ids(self, document_ids: list[str]) -> list[Document]:
        if not document_ids:
            return []
        statement = (
            select(DocumentRow)
            .options(*_document_loaders())
            .where(DocumentRow.id.in_(document_ids))
            .execution_options(populate_existing=True)
        )
        async with self._uow.session() as session:
            rows = {row.id: row for row in await session.scalars(statement)}
        return [
            _to_document(rows[document_id]) for document_id in document_ids if document_id in rows
        ]


class SqlAlchemyArticleRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.ArticleRepository`."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def find_by_content_hash(self, content_hash: str) -> list[Article]:
        statement = (
            select(ArticleRow)
            .where(ArticleRow.content_hash == content_hash)
            .order_by(ArticleRow.id)
        )
        async with self._uow.session() as session:
            rows = list(await session.scalars(statement))
        return [_to_article(row) for row in rows]

    async def save_canonical_link(self, article_id: str, canonical: Article) -> None:
        async with self._uow.session() as session:
            await session.execute(
                update(ArticleRow).where(ArticleRow.id == canonical.id).values(is_canonical=True)
            )
            if article_id != canonical.id:
                await session.execute(
                    update(ArticleRow).where(ArticleRow.id == article_id).values(is_canonical=False)
                )

    async def get(self, article_id: str) -> Article | None:
        statement = (
            select(ArticleRow)
            .options(selectinload(ArticleRow.passages))
            .where(ArticleRow.id == article_id)
            .execution_options(populate_existing=True)
        )
        async with self._uow.session() as session:
            row = await session.scalar(statement)
        return _to_article(row) if row is not None else None


class SqlAlchemyPassageRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.PassageRepository`."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def get(self, passage_id: str) -> PassageView | None:
        statement = (
            select(PassageRow)
            .options(_provenance_loader())
            .where(PassageRow.id == passage_id)
            .limit(1)
        )
        async with self._uow.session() as session:
            row = await session.scalar(statement)
        return _to_passage_view(row) if row is not None else None

    async def list_by_document(self, document_id: str) -> list[PassageView]:
        statement = (
            select(PassageRow)
            .join(ArticleRow, ArticleRow.id == PassageRow.article_id)
            .options(_provenance_loader())
            .where(ArticleRow.document_id == document_id)
            .order_by(ArticleRow.ord, PassageRow.ord)
        )
        async with self._uow.session() as session:
            rows = list(await session.scalars(statement))
        return [_to_passage_view(row) for row in rows]


class SqlAlchemyIngestionRunRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.IngestionRunRepository`."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def get(self, run_id: str) -> IngestionRun | None:
        async with self._uow.session() as session:
            row = await session.get(IngestionRunRow, run_id)
        return _to_run(row) if row is not None else None

    async def save(self, run: IngestionRun) -> None:
        async with self._uow.session() as session:
            row = await session.get(IngestionRunRow, run.id)
            if row is None:
                row = IngestionRunRow(id=run.id, shard_label=run.shard_label, status=run.status)
                session.add(row)
            row.shard_label = run.shard_label
            row.status = str(run.status)
            row.attempted = run.attempted
            row.accepted = run.accepted
            row.quarantined = run.quarantined
            row.failed = run.failed
            row.failure_reason = run.failure_reason
            row.updated_at = datetime.now(tz=UTC)

    async def latest(self, shard_label: str) -> IngestionRun | None:
        statement = (
            select(IngestionRunRow)
            .where(IngestionRunRow.shard_label == shard_label)
            .order_by(IngestionRunRow.created_at.desc(), IngestionRunRow.id.desc())
            .limit(1)
        )
        async with self._uow.session() as session:
            row = await session.scalar(statement)
        return _to_run(row) if row is not None else None


class SqlAlchemyCorpusSnapshotRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.CorpusSnapshotRepository`."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def get(self, snapshot_id: str) -> CorpusSnapshot | None:
        statement = (
            select(CorpusSnapshotRow)
            .options(selectinload(CorpusSnapshotRow.document_ids))
            .where(CorpusSnapshotRow.id == snapshot_id)
            .execution_options(populate_existing=True)
        )
        async with self._uow.session() as session:
            row = await session.scalar(statement)
        return _to_snapshot(row) if row is not None else None

    async def save(self, snapshot: CorpusSnapshot) -> None:
        async with self._uow.session() as session:
            row = await session.get(CorpusSnapshotRow, snapshot.id)
            if row is None:
                row = CorpusSnapshotRow(id=snapshot.id)
                session.add(row)
            row.label = snapshot.label
            row.manifest_hash = snapshot.manifest_hash
            row.pinned_at = snapshot.pinned_at
            row.index_version = snapshot.index_manifest.index_version
            row.embedding_model = snapshot.index_manifest.embedding_model
            row.searchable_since = snapshot.index_manifest.searchable_since
            row.passage_count = snapshot.index_manifest.passage_count
            await session.flush()

            await session.execute(
                delete(SnapshotDocumentRow).where(SnapshotDocumentRow.snapshot_id == snapshot.id)
            )
            session.add_all(
                [
                    SnapshotDocumentRow(snapshot_id=snapshot.id, document_id=document_id)
                    for document_id in snapshot.document_ids
                ]
            )

    async def list_document_ids(self, snapshot_id: str) -> list[str]:
        statement = (
            select(SnapshotDocumentRow.document_id)
            .where(SnapshotDocumentRow.snapshot_id == snapshot_id)
            .order_by(SnapshotDocumentRow.document_id)
        )
        async with self._uow.session() as session:
            return list(await session.scalars(statement))

    async def current_index_manifest(self) -> IndexManifest:
        statement = select(IndexManifestRow).where(IndexManifestRow.is_current.is_(True)).limit(1)
        async with self._uow.session() as session:
            row = await session.scalar(statement)
        if row is None:
            return IndexManifest(
                index_version=_ZERO_INDEX_VERSION,
                embedding_model="none",
                searchable_since=datetime.now(tz=UTC),
                passage_count=0,
            )
        return IndexManifest(
            index_version=row.index_version,
            embedding_model=row.embedding_model,
            searchable_since=row.searchable_since,
            passage_count=row.passage_count,
        )


class SqlAlchemyAuthorityRuleRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.AuthorityRuleRepository`.

    The rubric is frozen domain data; exposing it through the same port keeps the composition root
    uniform without inventing a table that no use case can mutate.
    """

    def __init__(self, unit_of_work: UnitOfWork | None = None) -> None:
        self._uow = unit_of_work

    async def for_claim_type(self, claim_type: ClaimType) -> AuthorityRule:
        if self._uow is not None:
            async with self._uow.session():
                return authority_rule(claim_type)
        return authority_rule(claim_type)

    async def list_all(self) -> list[AuthorityRule]:
        if self._uow is not None:
            async with self._uow.session():
                return [authority_rule(claim_type) for claim_type in ClaimType]
        return [authority_rule(claim_type) for claim_type in ClaimType]


# ── Row ↔ aggregate mapping ──────────────────────────────────────────────────


def _apply_document(row: DocumentRow, document: Document) -> None:
    row.source_uri = document.source_uri
    row.content_hash = document.content_hash
    row.source_type = str(document.source_type)
    row.language = str(document.language)
    row.tier = str(document.tier) if document.tier is not None else None
    quality = document.quality
    row.quality_method = str(quality.method) if quality is not None else None
    row.quality_confidence = quality.confidence if quality is not None else None
    row.quality_missing_glyph_rate = quality.missing_glyph_rate if quality is not None else None
    row.quality_page_count = quality.page_count if quality is not None else None
    row.extracted_text = document.extracted_text
    row.updated_at = datetime.now(tz=UTC)


def _publication_row(document: Document) -> PublicationRow:
    row = PublicationRow(document_id=document.id)
    _apply_publication(row, document)
    return row


def _apply_publication(row: PublicationRow, document: Document) -> None:
    row.outlet = document.publication.outlet
    row.published_on = document.publication.published_on
    row.medium = document.publication.medium


async def _sync_articles(session: AsyncSession, document: Document) -> None:
    existing = set(
        await session.scalars(select(ArticleRow.id).where(ArticleRow.document_id == document.id))
    )
    wanted = {article.id for article in document.articles}
    stale = existing - wanted
    if stale:
        await session.execute(delete(ArticleRow).where(ArticleRow.id.in_(stale)))

    for order, article in enumerate(document.articles):
        row = await session.get(ArticleRow, article.id)
        if row is None:
            row = ArticleRow(id=article.id, document_id=document.id)
            session.add(row)
        row.document_id = document.id
        row.ord = order
        row.headline = article.headline
        row.body = article.body
        row.content_hash = article_content_hash(article.body)
        row.page_from = article.page_from
        row.page_to = article.page_to
        row.language = str(article.language)
        row.is_canonical = article.is_canonical
        await session.flush()
        await _sync_passages(session, article)


async def _sync_passages(session: AsyncSession, article: Article) -> None:
    existing = set(
        await session.scalars(select(PassageRow.id).where(PassageRow.article_id == article.id))
    )
    wanted = {passage.id for passage in article.passages}
    stale = existing - wanted
    if stale:
        await session.execute(delete(PassageRow).where(PassageRow.id.in_(stale)))

    for order, passage in enumerate(article.passages):
        row = await session.get(PassageRow, passage.id)
        if row is None:
            row = PassageRow(id=passage.id, article_id=article.id)
            session.add(row)
        row.article_id = article.id
        row.ord = order
        row.text = passage.text
        row.offset_start = passage.offsets.start
        row.offset_end = passage.offsets.end
        row.speaker_kind = str(passage.speaker_kind)
        row.citable = passage.citable
        row.section = str(passage.section)


def _document_loaders() -> tuple[Any, ...]:
    """Reload the full aggregate even when the session already holds the document row."""
    return (
        selectinload(DocumentRow.publication),
        selectinload(DocumentRow.articles).selectinload(ArticleRow.passages),
    )


def _provenance_loader() -> Any:
    """Eager-load passage → article → document → publication (async sessions forbid lazy IO)."""
    return (
        joinedload(PassageRow.article)
        .joinedload(ArticleRow.document)
        .joinedload(DocumentRow.publication)
    )


def _to_document(row: DocumentRow) -> Document:
    publication_row = row.publication
    if publication_row is None:  # pragma: no cover - invariant enforced by save()
        raise ValueError(f"document {row.id} has no publication row")
    return Document(
        id=row.id,
        source_uri=row.source_uri,
        content_hash=row.content_hash,
        publication=Publication(
            outlet=publication_row.outlet,
            published_on=publication_row.published_on,
            medium=publication_row.medium,
        ),
        source_type=SourceType(row.source_type),
        language=LanguageTag(row.language),
        tier=AuthorityTier(row.tier) if row.tier is not None else None,
        quality=_to_quality(row),
        extracted_text=row.extracted_text,
        articles=[_to_article(article) for article in row.articles],
    )


def _to_quality(row: DocumentRow) -> ExtractionQuality | None:
    if row.quality_method is None:
        return None
    return ExtractionQuality(
        method=ExtractionMethod(row.quality_method),
        confidence=float(row.quality_confidence or 0.0),
        missing_glyph_rate=float(row.quality_missing_glyph_rate or 0.0),
        page_count=int(row.quality_page_count or 1),
    )


def _to_article(row: ArticleRow) -> Article:
    return Article(
        id=row.id,
        document_id=row.document_id,
        headline=row.headline,
        body=row.body,
        page_from=row.page_from,
        page_to=row.page_to,
        language=LanguageTag(row.language),
        is_canonical=row.is_canonical,
        passages=[_to_passage(passage, row.id, row.document_id) for passage in row.passages],
    )


def _to_passage(row: PassageRow, article_id: str, document_id: str) -> Passage:
    return Passage(
        id=row.id,
        article_id=article_id,
        document_id=document_id,
        ord=row.ord,
        text=row.text,
        offsets=Offsets(start=row.offset_start, end=row.offset_end),
        speaker_kind=SpeakerKind(row.speaker_kind),
        citable=row.citable,
        section=ArticleSection(row.section),
    )


def _to_passage_view(row: PassageRow) -> PassageView:
    article_row = row.article
    document_row = article_row.document
    publication_row = document_row.publication
    if publication_row is None:  # pragma: no cover - invariant enforced by save()
        raise ValueError(f"document {document_row.id} has no publication row")
    provenance = Provenance(
        outlet=publication_row.outlet,
        published_on=publication_row.published_on,
        medium=publication_row.medium,
        page_from=article_row.page_from,
        page_to=article_row.page_to,
        offsets=Offsets(start=row.offset_start, end=row.offset_end),
        source_uri=document_row.source_uri,
    )
    return PassageView(
        passage_id=row.id,
        article_id=article_row.id,
        document_id=document_row.id,
        text=row.text,
        provenance=provenance_view(provenance),
        speaker_kind=SpeakerKind(row.speaker_kind),
        citable=row.citable,
        source_type=SourceType(document_row.source_type),
    )


def _to_run(row: IngestionRunRow) -> IngestionRun:
    return IngestionRun(
        id=row.id,
        shard_label=row.shard_label,
        status=RunStatus(row.status),
        attempted=row.attempted,
        accepted=row.accepted,
        quarantined=row.quarantined,
        failed=row.failed,
        failure_reason=row.failure_reason,
    )


def _to_snapshot(row: CorpusSnapshotRow) -> CorpusSnapshot:
    return CorpusSnapshot(
        id=row.id,
        label=row.label,
        manifest_hash=row.manifest_hash,
        pinned_at=row.pinned_at,
        document_ids=sorted(member.document_id for member in row.document_ids),
        index_manifest=IndexManifest(
            index_version=row.index_version,
            embedding_model=row.embedding_model,
            searchable_since=row.searchable_since,
            passage_count=row.passage_count,
        ),
    )
