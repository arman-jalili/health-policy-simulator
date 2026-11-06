"""Native text extraction adapter (PyMuPDF).

Canonical: .pi/architecture/modules/evidence-corpus.md

The adapter reads local files only: fetching from object storage is an ingestion concern that runs
before extraction. Confidence is a heuristic that reflects usable text density, not layout quality;
the missing-glyph rate covers mapping failures in the PDF font table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from evidence_corpus.application.dto import ExtractionOutcome
from evidence_corpus.domain.errors import ExtractionFailed
from evidence_corpus.domain.values import ExtractionMethod, ExtractionQuality, PageTextFacts

MINIMUM_CHARS_FOR_FULL_CONFIDENCE = 300.0
REPLACEMENT_CHARACTERS = re.compile("[\ufffd\u25a1]")

_LOW_CONFIDENCE_FLOOR = 0.4


def local_path(source_uri: str) -> Path:
    """Resolve a `file://` URI or filesystem path; refuse schemes that must be fetched first."""
    if source_uri.startswith("file://"):
        return Path(source_uri.removeprefix("file://"))
    if "://" in source_uri:
        raise ExtractionFailed(source_uri, "only local paths can be extracted directly")
    return Path(source_uri)


class PyMuPdfExtractor:
    """Implements :class:`evidence_corpus.application.ports.ExtractionPort` with PyMuPDF."""

    async def probe(self, source_uri: str) -> PageTextFacts:
        path = local_path(source_uri)
        try:
            with pymupdf.open(path) as document:  # type: ignore[no-untyped-call]
                pages = document.page_count
                text = "".join(page.get_text() for page in document)
        except Exception as error:
            raise ExtractionFailed(source_uri, str(error)) from error

        if pages == 0:
            return PageTextFacts(
                has_text_layer=False,
                average_chars_per_page=0.0,
                missing_glyph_rate=0.0,
                page_count=0,
            )

        damaged = len(REPLACEMENT_CHARACTERS.findall(text))
        return PageTextFacts(
            has_text_layer=bool(text.strip()),
            average_chars_per_page=len(text) / pages,
            missing_glyph_rate=damaged / len(text) if text else 0.0,
            page_count=pages,
        )

    async def extract(self, source_uri: str) -> ExtractionOutcome:
        path = local_path(source_uri)
        try:
            with pymupdf.open(path) as document:  # type: ignore[no-untyped-call]
                pages = document.page_count
                page_texts = [page.get_text() for page in document]
        except Exception as error:
            raise ExtractionFailed(source_uri, str(error)) from error

        text = "\n".join(page_texts).strip()
        if not text:
            raise ExtractionFailed(source_uri, "no text layer found; route to OCR")

        damaged = len(REPLACEMENT_CHARACTERS.findall(text))
        chars_per_page = len(text) / max(pages, 1)
        confidence = _LOW_CONFIDENCE_FLOOR + (1.0 - _LOW_CONFIDENCE_FLOOR) * min(
            1.0, chars_per_page / MINIMUM_CHARS_FOR_FULL_CONFIDENCE
        )
        return ExtractionOutcome(
            document_id="",
            text=text,
            quality=ExtractionQuality(
                method=ExtractionMethod.NATIVE,
                confidence=round(confidence, 4),
                missing_glyph_rate=round(damaged / len(text), 4),
                page_count=max(pages, 1),
            ),
        )
