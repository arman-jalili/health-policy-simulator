"""Ports consumed by the EvidenceCorpus application layer.

Canonical: .pi/architecture/modules/evidence-corpus.md

Ports isolate vendor choices (PyMuPDF, Tesseract, PostgreSQL) from use-case orchestration. They are
declared here, implemented in `infrastructure/`, and never imported by `domain/`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from evidence_corpus.application.dto import ExtractionOutcome, IndexManifestView
from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.values import PageTextFacts


@runtime_checkable
class ExtractionPort(Protocol):
    """Native text extraction (PyMuPDF); probes whether a text layer exists."""

    async def probe(self, source_uri: str) -> PageTextFacts: ...

    async def extract(self, source_uri: str) -> ExtractionOutcome: ...


@runtime_checkable
class OcrPort(Protocol):
    """OCR fallback for scans without a text layer."""

    async def extract(self, source_uri: str) -> ExtractionOutcome: ...


@runtime_checkable
class IndexWriterPort(Protocol):
    """Persistence of searchable passages; idempotent per document."""

    async def upsert_passages(
        self, document_id: str, passages: Sequence[PassageView]
    ) -> IndexManifestView: ...

    async def revert_passage(self, passage_id: str, reason: str) -> None: ...

    async def search(self, query: str, limit: int = 20) -> list[str]: ...


@runtime_checkable
class ContentHasher(Protocol):
    """Content addressing so re-ingestion is detected instead of duplicated."""

    def hash(self, source_uri: str) -> str: ...
