"""Frozen error contract of the EvidenceRetrieval bounded context (ADR-004).

Canonical: .pi/architecture/modules/evidence-retrieval.md

Each error has a stable machine code and an HTTP status, so the API envelope never depends on
message wording. Codes are unique per context.
"""

from __future__ import annotations

from collections.abc import Sequence

from shared.errors import ConflictError, NotFoundError, ValidationFailedError


class PackFrozen(ConflictError):
    """A frozen pack is immutable; re-retrieval creates a new version (invariant 4)."""

    code = "PACK_FROZEN"

    def __init__(self, pack_id: str) -> None:
        super().__init__(f"evidence pack {pack_id} is frozen")


class AbsenceWithContradiction(ConflictError):
    """Absence must be truthful; it cannot be recorded when contradiction was found.

    Invariant 8: absence names the searches actually performed.
    """

    code = "ABSENCE_WITH_CONTRADICTION"

    def __init__(self, pack_id: str) -> None:
        super().__init__(
            f"evidence pack {pack_id} already contains contradicting evidence; "
            "absence would misreport the search"
        )


class CandidateWithoutProvenance(ValidationFailedError):
    """Every candidate must carry resolvable corpus provenance (invariant 2)."""

    code = "CANDIDATE_WITHOUT_PROVENANCE"

    def __init__(self, passage_ids: Sequence[str]) -> None:
        self.passage_ids = tuple(passage_ids)
        super().__init__("candidates without provenance: " + ", ".join(self.passage_ids))


class EvidencePackNotFound(NotFoundError):
    """The requested pack does not exist in this context."""

    code = "EVIDENCE_PACK_NOT_FOUND"

    def __init__(self, pack_id: str) -> None:
        super().__init__(f"evidence pack {pack_id} not found")
