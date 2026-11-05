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

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime

from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.errors import (
    AbsenceWithContradiction,
    CandidateWithoutProvenance,
    PackFrozen,
)
from evidence_retrieval.domain.events import (
    ContradictingEvidenceSurfaced,
    DomainEvent,
    EvidenceAbsenceRecorded,
    EvidencePackAssembled,
)
from evidence_retrieval.domain.values import (
    AbsenceFinding,
    ClaimText,
    PackId,
    SnapshotId,
    StanceLabel,
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
        if self.frozen:
            raise PackFrozen(str(self.id))
        self.candidates.append(candidate)
        if candidate.stance is StanceLabel.CONTRADICTING:
            self.events.append(
                ContradictingEvidenceSurfaced(
                    pack_id=str(self.id),
                    passage_id=str(candidate.passage_id),
                    stance=candidate.stance,
                )
            )

    def record_absence(self, queries: list[str], reason: str) -> None:
        """Record a truthful negative result; refused when contradiction is already present."""
        if self.frozen:
            raise PackFrozen(str(self.id))
        if any(c.stance is StanceLabel.CONTRADICTING for c in self.candidates):
            raise AbsenceWithContradiction(str(self.id))
        self.absence = AbsenceFinding(
            queries=tuple(queries),
            snapshot_id=self.snapshot_id,
            reason=reason,
        )
        self.events.append(
            EvidenceAbsenceRecorded(
                pack_id=str(self.id),
                queries=tuple(queries),
                snapshot_id=str(self.snapshot_id),
                reason=reason,
            )
        )

    def freeze(self) -> None:
        """Assert provenance and make the pack immutable, emitting the assembled event."""
        if self.frozen:
            raise PackFrozen(str(self.id))
        self.assert_every_candidate_has_provenance()
        self.frozen = True
        self.frozen_at = datetime.now(tz=UTC)
        self.events.append(
            EvidencePackAssembled(
                pack_id=str(self.id),
                claim_hash=_claim_hash(self.claim),
                candidate_count=len(self.candidates),
                has_absence=self.absence is not None,
                index_version=self.index_version,
            )
        )

    def assert_every_candidate_has_provenance(self) -> None:
        """Raise :class:`CandidateWithoutProvenance` when any candidate lacks provenance."""
        missing = [
            str(candidate.passage_id)
            for candidate in self.candidates
            if candidate.provenance is None
        ]
        if missing:
            raise CandidateWithoutProvenance(missing)

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        """Candidate identities in insertion order; stable for the same search result."""
        return tuple(str(candidate.passage_id) for candidate in self.candidates)


def _claim_hash(claim: ClaimText) -> str:
    """Hash the claim for the event payload without publishing raw claim text."""
    return hashlib.sha256(str(claim).encode("utf-8")).hexdigest()
