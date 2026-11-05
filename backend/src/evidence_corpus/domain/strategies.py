"""Article boundary strategies (domain service implementations).

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — concrete classes exist so call sites can already depend on the strategy port, but
segmentation behaviour is a stub until ISSUE segmentarticle lands.
"""

from __future__ import annotations

from evidence_corpus.domain.entities import Publication
from evidence_corpus.domain.values import ArticleDraft


class SingleArticleStrategy:
    """One document is one editorial unit (the common case for a press PDF)."""

    def segment(self, text: str, publication: Publication) -> list[ArticleDraft]:
        """TODO(segmentarticle): derive headline/dateline/body for a single article."""
        raise NotImplementedError("SingleArticleStrategy.segment is a frozen stub")


class ClippingDigestStrategy:
    """A digest page contains several clippings that must become distinct articles."""

    def segment(self, text: str, publication: Publication) -> list[ArticleDraft]:
        """TODO(segmentarticle): split a clipping digest into one draft per clipping."""
        raise NotImplementedError("ClippingDigestStrategy.segment is a frozen stub")
