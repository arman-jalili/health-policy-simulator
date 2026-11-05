"""Evaluation harness contract: labelled claims in, a measured recall report out.

Canonical: .pi/architecture/modules/evidence-retrieval.md

The harness is a tool, not an application service: it is invoked by CI and analysts, never by
request handling, so it lives at the module root and is not wired into the container.

The harness is deliberately not a domain concept (ADR-008). It asserts no threshold in code; a
labelled set of at least 50 claims produces a report that CI stores as an artifact. Quality targets
are read from the report, never compiled in.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from evidence_corpus.domain.values import ClaimType
from evidence_retrieval.application.services import SearchEvidenceCandidates
from evidence_retrieval.domain.values import SnapshotId


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """One manually labelled claim with the passages a human judged relevant."""

    claim: str
    claim_type: ClaimType
    snapshot_id: SnapshotId
    relevant_passage_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class RecallReport:
    """Measured recall; no target or pass/fail threshold is encoded here."""

    case_count: int
    recall_at_k: float
    per_case_recall: Mapping[str, float]


class EvaluationHarness:
    """Run a labelled set through the real search path and report recall."""

    def __init__(self, search: SearchEvidenceCandidates) -> None:
        self._search = search

    async def run(self, cases: Sequence[EvaluationCase], *, k: int = 10) -> RecallReport:
        """Return the measured report; the caller decides whether it is good enough."""
        raise NotImplementedError("EvaluationHarness.run is a frozen stub")
