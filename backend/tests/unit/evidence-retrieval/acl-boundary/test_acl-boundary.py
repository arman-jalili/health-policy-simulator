"""Contract freeze: the published language exposes references, never vectors."""

from __future__ import annotations

import dataclasses
from datetime import UTC, date, datetime

from tests.unit.evidence_retrieval_contract_helpers import SRC, field_names, public_fields

from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import Offsets
from evidence_retrieval.application.dto import (
    CandidateResult,
    EvidencePackResult,
    TraceResult,
)
from evidence_retrieval.domain.values import EvidenceScore, StanceLabel
from evidence_retrieval.interfaces.published import (
    EvidenceCandidateView,
    EvidencePackView,
    RetrievalTraceView,
    ScoreBreakdownView,
    to_claim_evidence_refs,
    to_published_pack,
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


def test_acl_maps_packs_to_refs_and_never_leaks_vectors() -> None:
    result = EvidencePackResult(
        pack_id="evp_1",
        claim="Kassenstellen",
        snapshot_id="snap_1",
        index_version="idx-1",
        candidates=[
            CandidateResult(
                passage_id="psg_1",  # type: ignore[arg-type]
                stance=StanceLabel.SUPPORTING,
                score=EvidenceScore(
                    authority=0.8,
                    lexical=0.7,
                    semantic=0.6,
                    recency=1.0,
                    directness=0.5,
                    final=3.6,
                ),
                provenance=ProvenanceView(
                    outlet="Der Standard",
                    published_on=date(2026, 10, 1),
                    medium="print",
                    page_from=1,
                    page_to=1,
                    offsets=Offsets(0, 10),
                    source_uri="s3://corpus/source.pdf",
                ),
            )
        ],
        absence=None,
        trace=TraceResult(
            embedding_model="text-embedding-3-large",
            reranker_model="cross-encoder",
            query_rewrite="Kassenstellen",
            stance_counts={StanceLabel.SUPPORTING: 1},
        ),
        frozen_at=datetime(2026, 11, 5, tzinfo=UTC),
    )

    view = to_published_pack(result)
    refs = to_claim_evidence_refs(view)

    assert [ref.passage_id for ref in refs] == ["psg_1"]
    assert not hasattr(refs[0], "text")
    assert "vector" not in repr(dataclasses.asdict(view))
