"""Contract freeze: value objects and entities of EvidenceRetrieval."""

from __future__ import annotations

from datetime import date

import pytest
from tests.unit.evidence_retrieval_contract_helpers import enum_values, field_names

from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import AuthorityTier, ClaimType, Offsets, SourceType
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.values import (
    AbsenceFinding,
    AuthorityWeight,
    ClaimText,
    CoverageReport,
    EvidenceScore,
    PackId,
    PassageId,
    QueryRewrite,
    RecencyPolicy,
    RetrievalQuery,
    SnapshotId,
    StanceLabel,
)


def _score() -> EvidenceScore:
    return EvidenceScore(
        authority=0.9,
        lexical=0.7,
        semantic=0.8,
        recency=1.0,
        directness=0.6,
        final=4.0,
    )


def _provenance() -> ProvenanceView:
    return ProvenanceView(
        outlet="Der Standard",
        published_on=date(2026, 10, 1),
        medium="print",
        page_from=1,
        page_to=1,
        offsets=Offsets(0, 10),
        source_uri="s3://corpus/source.pdf",
    )


def test_ids_are_distinct_new_types() -> None:
    assert PackId("evp_1") == "evp_1"
    assert SnapshotId("snap_1") == "snap_1"
    assert PassageId("psg_1") == "psg_1"
    assert ClaimText("claim") == "claim"


def test_stance_has_exactly_four_labels() -> None:
    assert enum_values(StanceLabel) == {
        "supporting",
        "contradicting",
        "contextual",
        "tangential",
    }


def test_evidence_score_exposes_every_component_and_reproduces_final() -> None:
    assert field_names(EvidenceScore) == [
        "authority",
        "lexical",
        "semantic",
        "recency",
        "directness",
        "final",
    ]
    score = _score()

    assert score.component_sum == 4.0
    with pytest.raises(ValueError, match="final"):
        EvidenceScore(
            authority=0.1,
            lexical=0.1,
            semantic=0.1,
            recency=0.1,
            directness=0.1,
            final=1.0,
        )


def test_recency_policy_is_parameterised_and_exempts_non_perishables() -> None:
    assert field_names(RecencyPolicy) == ["half_life_days", "exempt_source_types"]
    policy = RecencyPolicy()

    assert policy.is_exempt(SourceType.LEGISLATION) is True
    assert policy.is_exempt(SourceType.PRESS_REPORT) is False
    with pytest.raises(ValueError, match="positive"):
        RecencyPolicy(half_life_days=0)


def test_authority_weight_is_a_numeric_corpus_derived_value() -> None:
    assert field_names(AuthorityWeight) == ["tier", "weight"]
    weight = AuthorityWeight(tier=AuthorityTier.LEGISLATION, weight=1.0)

    assert weight.weight == 1.0
    with pytest.raises(ValueError, match="weight"):
        AuthorityWeight(tier=AuthorityTier.LEGISLATION, weight=1.1)


def test_query_rewrite_and_retrieval_query_are_value_objects() -> None:
    assert field_names(QueryRewrite) == ["original", "expanded"]
    assert field_names(RetrievalQuery) == ["claim", "claim_type", "snapshot_id", "limit"]

    rewrite = QueryRewrite(original="Kassenstellen", expanded="Kassenstellen OR Kasse")
    query = RetrievalQuery(
        claim=ClaimText("Kassenstellen"),
        claim_type=ClaimType.QUANTITATIVE,
        snapshot_id=SnapshotId("snap_1"),
        limit=10,
    )

    assert rewrite.expanded.startswith("Kassenstellen")
    assert query.limit == 10
    with pytest.raises(ValueError, match="limit"):
        RetrievalQuery(
            claim=ClaimText("claim"),
            claim_type=ClaimType.QUALITATIVE,
            snapshot_id=SnapshotId("snap_1"),
            limit=0,
        )


def test_absence_and_coverage_report_are_truthful_value_objects() -> None:
    assert field_names(AbsenceFinding) == ["queries", "snapshot_id", "reason"]
    finding = AbsenceFinding(
        queries=("Kassenstellen",),
        snapshot_id=SnapshotId("snap_1"),
        reason="no contradicting passage above threshold",
    )
    coverage = CoverageReport(
        stance_counts={StanceLabel.SUPPORTING: 2, StanceLabel.CONTRADICTING: 0},
        best_authority=AuthorityWeight(tier=AuthorityTier.OFFICIAL_STATISTICS, weight=0.9),
    )

    assert finding.queries == ("Kassenstellen",)
    assert coverage.total == 2
    with pytest.raises(ValueError, match="queries"):
        AbsenceFinding(queries=(), snapshot_id=SnapshotId("snap_1"), reason="none")


def test_candidate_and_trace_are_entities_with_stable_identity() -> None:
    assert field_names(EvidenceCandidate) == [
        "passage_id",
        "stance",
        "score",
        "provenance",
    ]
    assert field_names(RetrievalTrace) == [
        "embedding_model",
        "reranker_model",
        "query_rewrite",
        "stance_counts",
    ]

    candidate = EvidenceCandidate(
        passage_id=PassageId("psg_1"),
        stance=StanceLabel.SUPPORTING,
        score=_score(),
        provenance=_provenance(),
    )
    trace = RetrievalTrace(
        embedding_model="text-embedding-3-large",
        reranker_model="cross-encoder",
        query_rewrite=QueryRewrite("a", "a"),
        stance_counts={StanceLabel.SUPPORTING: 1},
    )

    assert candidate.passage_id == "psg_1"
    assert trace.stance_counts[StanceLabel.SUPPORTING] == 1
