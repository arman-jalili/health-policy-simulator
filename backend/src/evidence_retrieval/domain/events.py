"""Frozen domain-event payloads of the EvidenceRetrieval context (ADR-003, ADR-008).

Canonical: .pi/architecture/modules/evidence-retrieval.md

Event names are past-tense immutable facts. Payloads carry ids plus the minimum a consumer needs;
consumers re-read the pack for detail. fusion, score arithmetic, recency weighting and query
rewriting are log lines, not domain events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from evidence_retrieval.domain.values import StanceLabel


@dataclass(frozen=True, slots=True)
class EvidencePackAssembled:
    """A balanced, scored pack was frozen for a claim."""

    name: ClassVar[str] = "EvidencePackAssembled"
    pack_id: str
    claim_hash: str
    candidate_count: int
    has_absence: bool
    index_version: str


@dataclass(frozen=True, slots=True)
class ContradictingEvidenceSurfaced:
    """Evidence opposing the requester's position was included in the pack."""

    name: ClassVar[str] = "ContradictingEvidenceSurfaced"
    pack_id: str
    passage_id: str
    stance: StanceLabel


@dataclass(frozen=True, slots=True)
class EvidenceAbsenceRecorded:
    """A stance produced no qualifying evidence; the failed searches are recorded."""

    name: ClassVar[str] = "EvidenceAbsenceRecorded"
    pack_id: str
    queries: tuple[str, ...]
    snapshot_id: str
    reason: str


type DomainEvent = EvidencePackAssembled | ContradictingEvidenceSurfaced | EvidenceAbsenceRecorded
