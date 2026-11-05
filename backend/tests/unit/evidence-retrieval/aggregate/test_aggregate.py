"""Contract freeze: the EvidencePack aggregate boundary and method surface."""

from __future__ import annotations

import inspect

from tests.unit.evidence_retrieval_contract_helpers import field_names, parameter_names

from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.values import (
    AbsenceFinding,
    ClaimText,
    PackId,
    QueryRewrite,
    SnapshotId,
)


def test_pack_fields_are_frozen() -> None:
    assert field_names(EvidencePack) == [
        "id",
        "claim",
        "snapshot_id",
        "index_version",
        "trace",
        "candidates",
        "absence",
        "frozen",
        "frozen_at",
        "events",
    ]


def test_pack_is_an_aggregate_not_a_value_object() -> None:
    pack = EvidencePack(
        id=PackId("evp_1"),
        claim=ClaimText("Kassenstellen"),
        snapshot_id=SnapshotId("snap_1"),
        index_version="idx-1",
        trace=RetrievalTrace(
            embedding_model="text-embedding-3-large",
            reranker_model="cross-encoder",
            query_rewrite=QueryRewrite(original="Kassenstellen", expanded="Kassenstellen"),
            stance_counts={},
        ),
    )

    assert pack.candidates == []
    assert pack.absence is None
    assert pack.frozen is False
    assert pack.events == []


def test_add_candidate_accepts_one_candidate() -> None:
    assert parameter_names(EvidencePack.add_candidate) == ["self", "candidate"]
    candidate = inspect.signature(EvidencePack.add_candidate).parameters["candidate"]
    assert candidate.annotation is not None
    assert EvidenceCandidate.__name__ == "EvidenceCandidate"


def test_record_absence_names_queries_and_reason() -> None:
    assert parameter_names(EvidencePack.record_absence) == ["self", "queries", "reason"]
    assert AbsenceFinding.__name__ == "AbsenceFinding"


def test_freeze_and_provenance_assertion_are_separate_steps() -> None:
    assert parameter_names(EvidencePack.freeze) == ["self"]
    assert parameter_names(EvidencePack.assert_every_candidate_has_provenance) == ["self"]


def test_pack_records_the_index_version_and_trace_for_reproducibility() -> None:
    fields = field_names(EvidencePack)

    assert "index_version" in fields
    assert "trace" in fields
    assert field_names(RetrievalTrace) == [
        "embedding_model",
        "reranker_model",
        "query_rewrite",
        "stance_counts",
    ]
