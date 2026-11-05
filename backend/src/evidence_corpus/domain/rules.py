"""Concrete domain rules of EvidenceCorpus (ADR-008: domain services live in the domain layer).

Canonical: .pi/architecture/modules/evidence-corpus.md

The ports are declared in `services.py`; these are the executable rules they abstract. Keeping the
implementations in a separate module makes the port/implementation split explicit and keeps the
interface file free of behaviour.
"""

from __future__ import annotations

from evidence_corpus.domain.entities import Document, Passage
from evidence_corpus.domain.values import (
    MAX_MISSING_GLYPH_RATE,
    ExtractionMethod,
    PageTextFacts,
)

MINIMUM_CHARS_PER_PAGE = 200.0


class DefaultCitabilitySpec:
    """`has_provenance AND quality_ok AND source_type_known` (invariants 4, 5, 7)."""

    def is_satisfied(self, document: Document, passage: Passage) -> bool:
        return document.is_citable() and passage.citable and passage.provenance is not None


class PageFactsOcrSelection:
    """Route a document to OCR when the page facts show no usable text layer.

    OCR is chosen when the text layer is missing, the page is nearly empty, or the glyph damage is
    above the same tolerance the quality gate uses. Otherwise native extraction is cheaper and more
    faithful.
    """

    minimum_chars_per_page = MINIMUM_CHARS_PER_PAGE
    maximum_glyph_damage = MAX_MISSING_GLYPH_RATE

    def select(self, page_facts: PageTextFacts) -> ExtractionMethod:
        if not page_facts.has_text_layer:
            return ExtractionMethod.OCR
        if page_facts.average_chars_per_page < self.minimum_chars_per_page:
            return ExtractionMethod.OCR
        if page_facts.missing_glyph_rate > self.maximum_glyph_damage:
            return ExtractionMethod.OCR
        return ExtractionMethod.NATIVE
