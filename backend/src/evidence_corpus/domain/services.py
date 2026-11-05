"""Domain services of EvidenceCorpus (business rules that do not belong to one entity).

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — interfaces only. Implementations are provided by the owning issues:
`CitabilitySpec` (specification), `NativeVsOcrSelection` (strategy), `ArticleBoundaryStrategy`
(strategy). None of these may depend on vendor code: extraction and OCR live in infrastructure.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from evidence_corpus.domain.entities import Document, Passage, Publication
from evidence_corpus.domain.values import ArticleDraft, ExtractionMethod, PageTextFacts


@runtime_checkable
class CitabilitySpec(Protocol):
    """Composable rule: provenance present AND quality acceptable AND source type known."""

    def is_satisfied(self, document: Document, passage: Passage) -> bool: ...


@runtime_checkable
class NativeVsOcrSelection(Protocol):
    """Decide the extraction route from page-level facts (two real variants)."""

    def select(self, page_facts: PageTextFacts) -> ExtractionMethod: ...


@runtime_checkable
class ArticleBoundaryStrategy(Protocol):
    """Derive article boundaries for one document text.

    A clipping digest needs different rules than a single article, hence a strategy with a
    `SingleArticleStrategy` and a `ClippingDigestStrategy` implementation.
    """

    def segment(self, text: str, publication: Publication) -> list[ArticleDraft]: ...
