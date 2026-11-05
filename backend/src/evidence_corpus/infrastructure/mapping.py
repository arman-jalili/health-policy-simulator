"""Mapping between aggregate state and the published language (no ORM, no framework).

Canonical: .pi/architecture/modules/evidence-corpus.md
"""

from __future__ import annotations

from evidence_corpus.domain.entities import Article, Document, Passage
from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Provenance


def provenance_for(document: Document, article: Article, passage: Passage) -> Provenance:
    """Resolve the locator bundle for a passage; page and offsets come from the aggregate."""
    return Provenance(
        outlet=document.publication.outlet,
        published_on=document.publication.published_on,
        medium=document.publication.medium,
        page_from=article.page_from,
        page_to=article.page_to,
        offsets=passage.offsets,
        source_uri=document.source_uri,
    )


def provenance_view(provenance: Provenance) -> ProvenanceView:
    return ProvenanceView(
        outlet=provenance.outlet,
        published_on=provenance.published_on,
        medium=provenance.medium,
        page_from=provenance.page_from,
        page_to=provenance.page_to,
        offsets=provenance.offsets,
        source_uri=provenance.source_uri,
    )


def passage_view(document: Document, article: Article, passage: Passage) -> PassageView:
    provenance = passage.provenance or provenance_for(document, article, passage)
    return PassageView(
        passage_id=passage.id,
        article_id=article.id,
        document_id=document.id,
        text=passage.text,
        provenance=provenance_view(provenance),
        speaker_kind=passage.speaker_kind,
        citable=passage.citable,
        source_type=document.source_type,
    )
