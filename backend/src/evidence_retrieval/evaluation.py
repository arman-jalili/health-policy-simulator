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
from evidence_retrieval.application.commands import SearchEvidenceCandidatesRequest
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
    retrieval_mode: str = "unknown"


class EvaluationHarness:
    """Run a labelled set through the real search path and report recall."""

    def __init__(
        self, search: SearchEvidenceCandidates, *, retrieval_mode: str = "unknown"
    ) -> None:
        self._search = search
        self._retrieval_mode = retrieval_mode

    async def run(self, cases: Sequence[EvaluationCase], *, k: int = 10) -> RecallReport:
        """Return the measured report; the caller decides whether it is good enough."""
        if k < 1:
            raise ValueError("k must be at least 1")
        if not cases:
            raise ValueError("at least one labelled case is required")

        per_case: dict[str, float] = {}
        for case in cases:
            result = await self._search.execute(
                SearchEvidenceCandidatesRequest(
                    claim=case.claim,
                    claim_type=case.claim_type,
                    snapshot_id=str(case.snapshot_id),
                    limit=k,
                )
            )
            retrieved = {str(candidate.passage_id) for candidate in result.candidates}
            relevant = set(case.relevant_passage_ids)
            per_case[case.claim] = len(retrieved & relevant) / len(relevant) if relevant else 0.0

        return RecallReport(
            case_count=len(cases),
            recall_at_k=sum(per_case.values()) / len(per_case),
            per_case_recall=per_case,
            retrieval_mode=self._retrieval_mode,
        )
