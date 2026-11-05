"""Contract freeze: a labelled evaluation harness, with no threshold in code."""

from __future__ import annotations

from tests.unit.evidence_retrieval_contract_helpers import (
    SRC,
    field_names,
    parameter_names,
)

from evidence_corpus.domain.values import ClaimType
from evidence_retrieval.application.commands import SearchEvidenceCandidatesRequest
from evidence_retrieval.application.dto import CandidateResult, SearchCandidatesResult
from evidence_retrieval.domain.values import EvidenceScore, SnapshotId, StanceLabel
from evidence_retrieval.evaluation import (
    EvaluationCase,
    EvaluationHarness,
    RecallReport,
)


def test_case_carries_manual_labels_and_the_snapshot() -> None:
    assert field_names(EvaluationCase) == [
        "claim",
        "claim_type",
        "snapshot_id",
        "relevant_passage_ids",
    ]


def test_report_is_a_measurement_not_a_pass_fail_verdict() -> None:
    fields = field_names(RecallReport)

    assert fields == ["case_count", "recall_at_k", "per_case_recall", "retrieval_mode"]
    assert not any("threshold" in name or "passed" in name for name in fields)


def test_harness_runs_a_labelled_set_at_a_chosen_k() -> None:
    assert parameter_names(EvaluationHarness.run) == ["self", "cases", "k"]


def test_no_recall_threshold_is_compiled_into_the_module() -> None:
    source = (SRC / "evaluation.py").read_text(encoding="utf-8")

    assert "MIN_RECALL" not in source
    assert "target_recall" not in source
    assert "assert recall" not in source


class _FakeSearch:
    def __init__(self, hits: dict[str, str]) -> None:
        self.hits = hits

    async def execute(self, request: SearchEvidenceCandidatesRequest) -> SearchCandidatesResult:
        passage_id = self.hits.get(request.claim, "psg_miss")
        return SearchCandidatesResult(
            candidates=[
                CandidateResult(
                    passage_id=passage_id,  # type: ignore[arg-type]
                    stance=StanceLabel.SUPPORTING,
                    score=EvidenceScore(
                        authority=0.8,
                        lexical=0.7,
                        semantic=0.6,
                        recency=1.0,
                        directness=0.5,
                        final=3.6,
                    ),
                    provenance=None,
                )
            ]
        )


async def test_fifty_labelled_claims_produce_a_recall_report() -> None:
    cases = [
        EvaluationCase(
            claim=f"claim-{index}",
            claim_type=ClaimType.QUALITATIVE,
            snapshot_id=SnapshotId("snap_1"),
            relevant_passage_ids=frozenset({f"psg_{index}"}),
        )
        for index in range(50)
    ]
    search = _FakeSearch({case.claim: f"psg_{index}" for index, case in enumerate(cases)})
    harness = EvaluationHarness(search, retrieval_mode="lexical")  # type: ignore[arg-type]

    report = await harness.run(cases, k=10)

    assert report.case_count == 50
    assert report.retrieval_mode == "lexical"
    assert report.recall_at_k == 1.0
    assert len(report.per_case_recall) == 50
    assert not hasattr(report, "threshold")
