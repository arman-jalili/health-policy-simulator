"""Contract freeze: a labelled evaluation harness, with no threshold in code."""

from __future__ import annotations

from tests.unit.evidence_retrieval_contract_helpers import (
    SRC,
    field_names,
    parameter_names,
)

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

    assert fields == ["case_count", "recall_at_k", "per_case_recall"]
    assert not any("threshold" in name or "passed" in name for name in fields)


def test_harness_runs_a_labelled_set_at_a_chosen_k() -> None:
    assert parameter_names(EvaluationHarness.run) == ["self", "cases", "k"]


def test_no_recall_threshold_is_compiled_into_the_module() -> None:
    source = (SRC / "evaluation.py").read_text(encoding="utf-8")

    assert "MIN_RECALL" not in source
    assert "target_recall" not in source
    assert "assert recall" not in source
