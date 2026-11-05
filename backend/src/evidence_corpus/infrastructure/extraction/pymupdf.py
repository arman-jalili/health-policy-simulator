"""PyMuPDF text extraction adapter.

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — vendor adapter surface only; extraction behaviour lands with the
`ExtractDocumentText` implementation issue.
"""

from __future__ import annotations

from evidence_corpus.application.dto import ExtractionOutcome
from evidence_corpus.domain.values import PageTextFacts


class PyMuPdfExtractor:
    """Native text-layer extractor (implements :class:`ExtractionPort`)."""

    async def probe(self, source_uri: str) -> PageTextFacts:
        raise NotImplementedError("PyMuPdfExtractor.probe is a frozen stub")

    async def extract(self, source_uri: str) -> ExtractionOutcome:
        raise NotImplementedError("PyMuPdfExtractor.extract is a frozen stub")
