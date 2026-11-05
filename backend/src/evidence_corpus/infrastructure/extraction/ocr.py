"""OCR fallback adapter for scans without a text layer.

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — adapter surface only; OCR behaviour lands with the OCR issue.
"""

from __future__ import annotations

from evidence_corpus.application.dto import ExtractionOutcome


class TesseractOcrExtractor:
    """OCR extractor (implements :class:`OcrPort`); selected by `NativeVsOcrSelection`."""

    async def extract(self, source_uri: str) -> ExtractionOutcome:
        raise NotImplementedError("TesseractOcrExtractor.extract is a frozen stub")
