"""ORM models owned by the EvidenceCorpus context (ADR-002).

Canonical: .pi/architecture/modules/evidence-corpus.md

Table names follow the ADR-002 ownership rule ``evidence_corpus_<entity>``. These models stay
private to ``infrastructure/repository``: the domain never imports them and the application only
sees the repository ports. Migrations ``0101``/``0103`` are the authority for the schema; this
module mirrors them so ORM queries and migrations cannot drift silently.

Publications are modelled as a 1:1 owned row rather than columns on the document so the publication
value object keeps a single representation. Passages denormalise ``article_id`` only; provenance is
reconstructed from the document publication plus the article page range and the passage offsets, so
a citation never depends on a duplicated copy of the metadata.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db import Base


class DocumentRow(Base):
    """Aggregate root row: a physical source file with extraction state."""

    __tablename__ = "evidence_corpus_document"
    __table_args__ = (
        Index("ix_evidence_corpus_document_content_hash", "content_hash", unique=True),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    tier: Mapped[str | None] = mapped_column(String(40), nullable=True)
    quality_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quality_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_missing_glyph_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    publication: Mapped[PublicationRow | None] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    articles: Mapped[list[ArticleRow]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ArticleRow.ord",
        lazy="selectin",
    )


class PublicationRow(Base):
    """The outlet issue/edition a document was published in (1:1 owned by the document)."""

    __tablename__ = "evidence_corpus_publication"

    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("evidence_corpus_document.id", ondelete="CASCADE"),
        primary_key=True,
    )
    outlet: Mapped[str] = mapped_column(String(200), nullable=False)
    published_on: Mapped[date] = mapped_column(Date, nullable=False)
    medium: Mapped[str] = mapped_column(String(16), nullable=False)

    document: Mapped[DocumentRow] = relationship(back_populates="publication")


class ArticleRow(Base):
    """Editorial unit segmented out of a document."""

    __tablename__ = "evidence_corpus_article"
    __table_args__ = (
        Index("ix_evidence_corpus_article_document_id", "document_id"),
        Index("ix_evidence_corpus_article_content_hash", "content_hash"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("evidence_corpus_document.id", ondelete="CASCADE"),
        nullable=False,
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Normalised body digest: duplicate detection is an indexed lookup, not a full scan.
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    page_from: Mapped[int] = mapped_column(Integer, nullable=False)
    page_to: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    is_canonical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    document: Mapped[DocumentRow] = relationship(back_populates="articles")
    passages: Mapped[list[PassageRow]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        order_by="PassageRow.ord",
        lazy="selectin",
    )


class PassageRow(Base):
    """Smallest citable text span; the unit indexed, retrieved and cited."""

    __tablename__ = "evidence_corpus_passage"
    __table_args__ = (Index("ix_evidence_corpus_passage_article_id", "article_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    article_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("evidence_corpus_article.id", ondelete="CASCADE"),
        nullable=False,
    )
    ord: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    offset_start: Mapped[int] = mapped_column(Integer, nullable=False)
    offset_end: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    citable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    section: Mapped[str] = mapped_column(String(16), nullable=False)

    article: Mapped[ArticleRow] = relationship(back_populates="passages")


class CorpusSnapshotRow(Base):
    """Immutable manifest of the documents and index version a run may search."""

    __tablename__ = "evidence_corpus_snapshot"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    pinned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    index_version: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    searchable_since: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    passage_count: Mapped[int] = mapped_column(Integer, nullable=False)

    document_ids: Mapped[list[SnapshotDocumentRow]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SnapshotDocumentRow(Base):
    """Membership of a document in a pinned snapshot manifest."""

    __tablename__ = "evidence_corpus_snapshot_document"

    snapshot_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("evidence_corpus_snapshot.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    snapshot: Mapped[CorpusSnapshotRow] = relationship(back_populates="document_ids")


class IngestionRunRow(Base):
    """One auditable batch execution: outcome counts and retry lineage."""

    __tablename__ = "evidence_corpus_ingestion_run"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shard_label: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarantined: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcomes: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
