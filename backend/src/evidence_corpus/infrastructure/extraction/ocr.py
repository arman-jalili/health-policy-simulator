"""OCR fallback adapter for scans without a text layer.

Canonical: .pi/architecture/modules/evidence-corpus.md

Rasterises pages with PyMuPDF and reads them with Tesseract. The vendor dependency is optional at
import time: if the OCR stack is missing, extraction fails with `ExtractionFailed` instead of
silently returning empty text, because empty text would look like a quarantine decision.
"""

from __future__ import annotations

import io

import pymupdf

from evidence_corpus.application.dto import ExtractionOutcome
from evidence_corpus.domain.errors import ExtractionFailed
from evidence_corpus.domain.values import ExtractionMethod, ExtractionQuality
from evidence_corpus.infrastructure.extraction.pymupdf import local_path


class TesseractOcrExtractor:
    """Implements :class:`evidence_corpus.application.ports.OcrPort`."""

    def __init__(self, language: str = "deu") -> None:
        self._language = language

    async def extract(self, source_uri: str) -> ExtractionOutcome:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as error:  # pragma: no cover - optional vendor stack
            raise ExtractionFailed(source_uri, "pytesseract/Pillow not installed") from error

        path = local_path(source_uri)
        try:
            with pymupdf.open(path) as document:  # type: ignore[no-untyped-call]
                pages = document.page_count
                images = [
                    Image.open(io.BytesIO(page.get_pixmap(dpi=300).tobytes("png")))
                    for page in document
                ]
        except Exception as error:
            raise ExtractionFailed(source_uri, str(error)) from error

        texts: list[str] = []
        confidences: list[float] = []
        try:
            for image in images:
                texts.append(pytesseract.image_to_string(image, lang=self._language))
                data = pytesseract.image_to_data(
                    image, lang=self._language, output_type=pytesseract.Output.DICT
                )
                confidences.extend(
                    float(value) / 100.0
                    for value in data["conf"]
                    if str(value).lstrip("-").isdigit() and float(value) >= 0
                )
        except Exception as error:  # pragma: no cover - vendor failure
            raise ExtractionFailed(source_uri, f"tesseract failed: {error}") from error

        text = "\n".join(texts).strip()
        if not text:
            raise ExtractionFailed(source_uri, "OCR produced no text")

        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        damaged = sum(text.count(marker) for marker in ("\ufffd", "\u25a1"))
        return ExtractionOutcome(
            document_id="",
            text=text,
            quality=ExtractionQuality(
                method=ExtractionMethod.OCR,
                confidence=round(confidence, 4),
                missing_glyph_rate=round(damaged / len(text), 4),
                page_count=max(pages, 1),
            ),
        )
