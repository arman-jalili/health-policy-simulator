"""The EvidencePack aggregate — the frozen, balanced bundle for one claim.

Canonical: .pi/architecture/modules/evidence-retrieval.md

CONTRACT FREEZE — aggregate boundary, fields and method signatures are frozen; behaviour is a stub
raising ``NotImplementedError`` until the aggregate implementation issue lands.

Invariants:
1. a pack records search coverage and an absence finding for any stance with no result;
2. every candidate carries resolvable corpus provenance;
3. every candidate has an inspectable weight breakdown;
4. a frozen pack is immutable; re-retrieval creates a new version;
5. the pack references the index version and reranker model that produced it;
6. authority comes from the corpus rubric, never from retrieval;
7. recency exemptions keep non-perishable sources at full weight;
8. absence names the queries and snapshot actually searched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.events import DomainEvent
from evidence_retrieval.domain.values import (
    AbsenceFinding,
    ClaimText,
    PackId,
    SnapshotId,
)


@dataclass(slots=True)
class EvidencePack:
    """Aggregate root: candidates, absence, trace and a one-way freeze."""

    id: PackId
    claim: ClaimText
    snapshot_id: SnapshotId
    index_version: str
    trace: RetrievalTrace
    candidates: list[EvidenceCandidate] = field(default_factory=list)
    absence: AbsenceFinding | None = None
    frozen: bool = False
    frozen_at: datetime | None = None
    events: list[DomainEvent] = field(default_factory=list)

    def add_candidate(self, candidate: EvidenceCandidate) -> None:
        """Append a candidate; refused after ``freeze()`` with :class:`PackFrozen`."""
        raise NotImplementedError("EvidencePack.add_candidate is a frozen stub")

    def record_absence(self, queries: list[str], reason: str) -> None:
        """Record a truthful negative result; refused when contradiction is already present."""
        raise NotImplementedError("EvidencePack.record_absence is a frozen stub")

    def freeze(self) -> None:
        """Assert provenance and make the pack immutable, emitting the assembled event."""
        raise NotImplementedError("EvidencePack.freeze is a frozen stub")

    def assert_every_candidate_has_provenance(self) -> None:
        """Raise :class:`CandidateWithoutProvenance` when any candidate lacks provenance."""
        raise NotImplementedError(
            "EvidencePack.assert_every_candidate_has_provenance is a frozen stub"
        )
