"""Contract freeze: every score component is exposed and final is reproducible."""

from __future__ import annotations

from fastapi import FastAPI
from tests.unit.evidence_retrieval_contract_helpers import field_names

from evidence_corpus.domain.values import AuthorityTier
from evidence_retrieval.application.dto import CandidateScoreResult, ScoreBreakdownResult
from evidence_retrieval.domain.services import ScoreEvidenceCandidates
from evidence_retrieval.domain.values import AuthorityWeight, EvidenceScore
from evidence_retrieval.interfaces.http.router import router


def test_score_fields_are_exactly_the_five_components_plus_final() -> None:
    assert field_names(EvidenceScore) == [
        "authority",
        "lexical",
        "semantic",
        "recency",
        "directness",
        "final",
    ]


def test_final_is_the_sum_of_the_weighted_components() -> None:
    score = EvidenceScore(
        authority=0.4,
        lexical=0.2,
        semantic=0.1,
        recency=1.0,
        directness=0.3,
        final=2.0,
    )

    assert score.component_sum == 2.0
    assert score.final == score.component_sum


def test_breakdown_dtos_expose_passage_and_score_only() -> None:
    assert field_names(CandidateScoreResult) == ["passage_id", "score"]
    assert field_names(ScoreBreakdownResult) == ["pack_id", "candidates"]


def test_score_endpoint_is_frozen_in_openapi() -> None:
    app = FastAPI()
    app.include_router(router)
    paths = app.openapi()["paths"]

    assert "get" in paths["/api/v1/evidence/packs/{pack_id}/scores"]
    assert (
        paths["/api/v1/evidence/packs/{pack_id}/scores"]["get"]["x-required-scope"] == "runs:read"
    )


def test_scoring_service_preserves_every_component_and_reproduces_final() -> None:
    score = ScoreEvidenceCandidates().score(
        authority=AuthorityWeight(tier=AuthorityTier.LEGISLATION, weight=0.9),
        lexical=0.7,
        semantic=0.6,
        recency=1.0,
        directness=0.4,
    )

    assert (score.authority, score.lexical, score.semantic) == (0.9, 0.7, 0.6)
    assert (score.recency, score.directness) == (1.0, 0.4)
    assert score.final == score.component_sum
