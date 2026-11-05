"""Contract freeze: the router surface and composition container are fixed."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from tests.unit.evidence_retrieval_contract_helpers import field_names

from evidence_retrieval.composition import EvidenceRetrievalContainer, build_container
from evidence_retrieval.interfaces.http.router import router

EXPECTED_ROUTES = {
    "/api/v1/evidence/candidates": ("post", "runs:read"),
    "/api/v1/evidence/packs": ("post", "runs:write"),
    "/api/v1/evidence/packs/{pack_id}": ("get", "runs:read"),
    "/api/v1/evidence/packs/{pack_id}/scores": ("get", "runs:read"),
    "/api/v1/evidence/packs/{pack_id}/reweight": ("post", "runs:write"),
}


def test_router_freezes_all_five_endpoints_and_scopes() -> None:
    app = FastAPI()
    app.include_router(router)
    paths = app.openapi()["paths"]

    assert set(paths) == set(EXPECTED_ROUTES)
    for path, (method, scope) in EXPECTED_ROUTES.items():
        assert paths[path][method]["x-required-scope"] == scope


def test_container_freezes_every_port_and_use_case() -> None:
    assert field_names(EvidenceRetrievalContainer) == [
        "packs",
        "passage_search",
        "embeddings",
        "reranker",
        "query_rewrite",
        "readiness",
        "fusion",
        "stance_classifier",
        "scorer",
        "recency",
        "clock",
        "search_candidates",
        "assemble_pack",
        "get_pack",
        "get_score_breakdown",
        "reweight_pack",
        "unit_of_work",
    ]


def test_builder_is_a_todo_until_the_wiring_issue() -> None:
    with pytest.raises(NotImplementedError, match="TODO\\(wiring\\)"):
        build_container(SimpleNamespace(persistence="postgres"))  # type: ignore[arg-type]


def test_router_is_not_mounted_before_wiring() -> None:
    from evidence_retrieval.interfaces.http.router import router as retrieval_router

    assert retrieval_router.prefix == "/api/v1"
    assert retrieval_router.tags == ["evidence-retrieval"]
