"""Contract freeze: the hybrid search surface and German compound handling."""

from __future__ import annotations

from fastapi import FastAPI
from tests.unit.evidence_retrieval_contract_helpers import (
    field_names,
    parameter_names,
)

from evidence_retrieval.application.commands import SearchEvidenceCandidatesRequest
from evidence_retrieval.application.ports import EmbeddingPort, RerankerPort
from evidence_retrieval.domain.repositories import PassageSearchPort
from evidence_retrieval.domain.services import ReciprocalRankFusion
from evidence_retrieval.domain.values import QueryRewrite
from evidence_retrieval.infrastructure.query_rewrite import GermanQueryRewrite
from evidence_retrieval.interfaces.http.router import router


def test_corpus_search_port_is_lexical_dense_agnostic() -> None:
    assert parameter_names(PassageSearchPort.search) == [
        "self",
        "query",
        "snapshot_id",
        "limit",
    ]


def test_fusion_is_a_strategy_with_a_smoothing_constant() -> None:
    assert parameter_names(ReciprocalRankFusion.fuse) == ["self", "rankings", "k"]


def test_vendor_ports_keep_vectors_and_reranking_out_of_the_domain() -> None:
    assert hasattr(EmbeddingPort, "embed")
    assert hasattr(RerankerPort, "rerank")


def test_query_rewrite_is_deterministic_and_explicit() -> None:
    assert field_names(QueryRewrite) == ["original", "expanded"]
    rewrite = QueryRewrite(original="Kassenstellen", expanded="Kassenstellen OR Kasse")

    assert rewrite.original == "Kassenstellen"
    assert "Kasse" in rewrite.expanded


def test_search_request_carries_claim_type_snapshot_and_limit() -> None:
    assert field_names(SearchEvidenceCandidatesRequest) == [
        "claim",
        "claim_type",
        "snapshot_id",
        "limit",
    ]


def test_candidates_endpoint_is_frozen_in_openapi() -> None:
    app = FastAPI()
    app.include_router(router)
    operation = app.openapi()["paths"]["/api/v1/evidence/candidates"]["post"]

    assert operation["x-required-scope"] == "runs:read"
    assert "SearchCandidatesBody" in str(operation["requestBody"])


def test_german_rewrite_expands_a_compound_but_keeps_the_original_term_first() -> None:
    rewrite = GermanQueryRewrite().rewrite("Kassenstellen")

    terms = rewrite.expanded.split(" OR ")

    assert rewrite.original == "Kassenstellen"
    assert terms[0] == "Kassenstellen"
    assert "Kasse" in terms
    assert "stellen" in terms
    assert len(terms) == len(set(terms))


def test_german_rewrite_is_deterministic() -> None:
    first = GermanQueryRewrite().rewrite("Kassenstellen")
    second = GermanQueryRewrite().rewrite("Kassenstellen")

    assert first == second
