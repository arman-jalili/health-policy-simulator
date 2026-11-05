"""Contract freeze: the published language exposes references, never vectors."""

from __future__ import annotations

from tests.unit.evidence_retrieval_contract_helpers import SRC, field_names, public_fields

from evidence_retrieval.interfaces.published import (
    EvidenceCandidateView,
    EvidencePackView,
    RetrievalTraceView,
    ScoreBreakdownView,
)

PUBLISHED = SRC / "interfaces" / "published.py"


def test_published_pack_has_no_vector_or_corpus_row_fields() -> None:
    fields = field_names(EvidencePackView)

    assert fields == [
        "pack_id",
        "claim",
        "snapshot_id",
        "index_version",
        "candidates",
        "absence",
        "trace",
        "frozen_at",
    ]
    assert not any("vector" in name for name in fields)
    assert not any(name.startswith("raw_") for name in fields)


def test_published_candidate_is_a_reference_with_provenance_only() -> None:
    fields = field_names(EvidenceCandidateView)

    assert fields == ["passage_id", "stance", "score", "provenance"]
    assert "text" not in fields
    assert "vector" not in " ".join(fields)


def test_trace_publishes_model_names_but_never_vectors() -> None:
    fields = field_names(RetrievalTraceView)

    assert fields == ["embedding_model", "reranker_model", "query_rewrite", "stance_counts"]
    assert "embedding" in fields[0]
    assert not any("vector" in name for name in fields)


def test_breakdown_view_is_reference_only() -> None:
    assert field_names(ScoreBreakdownView) == ["pack_id", "candidates"]


def test_published_module_does_not_import_pgvector_or_orm_types() -> None:
    imports = [
        line
        for line in PUBLISHED.read_text(encoding="utf-8").splitlines()
        if line.startswith(("import ", "from "))
    ]

    assert not any("pgvector" in line or "sqlalchemy" in line for line in imports)
    assert public_fields(PUBLISHED, "EvidencePackView") == set(field_names(EvidencePackView))
