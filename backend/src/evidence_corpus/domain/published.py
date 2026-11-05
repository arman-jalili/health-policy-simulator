"""Open-host published language of EvidenceCorpus (ADR-003).

Canonical: .pi/architecture/modules/evidence-corpus.md

Consumers (EvidenceRetrieval, DecisionBrief) read these immutable views instead of the corpus's
tables. The contract is deliberately framework-free: no ORM, no pydantic, no FastAPI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from evidence_corpus.domain.values import Offsets, SpeakerKind


@dataclass(frozen=True, slots=True)
class ProvenanceView:
    """Everything a reader needs to open the source and verify the citation."""

    outlet: str
    published_on: date
    medium: str
    page_from: int
    page_to: int
    offsets: Offsets
    source_uri: str


@dataclass(frozen=True, slots=True)
class PassageView:
    """The smallest citable span as published to other contexts."""

    passage_id: str
    article_id: str
    document_id: str
    text: str
    provenance: ProvenanceView
    speaker_kind: SpeakerKind
    citable: bool
