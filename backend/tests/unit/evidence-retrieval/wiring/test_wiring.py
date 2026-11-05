"""Wiring: the router is mounted and the container binds real adapters."""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from tests.conftest import TEST_DATABASE_URL, StubDatabase
from tests.unit.evidence_retrieval_contract_helpers import SRC, field_names, imported_names

from evidence_retrieval.composition import EvidenceRetrievalContainer
from evidence_retrieval.infrastructure.adapters import (
    CorpusPassageSearch,
    LexicalEmbedding,
    NoopReranker,
    RuleBasedStanceModel,
    StaticRetrievalReadiness,
)
from evidence_retrieval.infrastructure.memory import InMemoryEvidencePackRepository
from evidence_retrieval.infrastructure.query_rewrite import GermanQueryRewrite
from evidence_retrieval.interfaces.http.router import router
from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence

EXPECTED_ROUTES = {
    "/api/v1/evidence/candidates": ("post", "runs:read"),
    "/api/v1/evidence/packs": ("post", "runs:write"),
    "/api/v1/evidence/packs/{pack_id}": ("get", "runs:read"),
    "/api/v1/evidence/packs/{pack_id}/scores": ("get", "runs:read"),
    "/api/v1/evidence/packs/{pack_id}/reweight": ("post", "runs:write"),
}


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        persistence=Persistence.MEMORY,
        auth_mode=AuthMode.DEMO,
    )


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


def test_memory_wiring_binds_corpus_ports_not_tables() -> None:
    app = create_app(_settings())
    container = app.state.evidence_retrieval

    assert isinstance(container.packs, InMemoryEvidencePackRepository)
    assert isinstance(container.passage_search, CorpusPassageSearch)
    assert isinstance(container.embeddings, LexicalEmbedding)
    assert isinstance(container.reranker, NoopReranker)
    assert isinstance(container.query_rewrite, GermanQueryRewrite)
    assert isinstance(container.readiness, StaticRetrievalReadiness)
    assert isinstance(container.stance_classifier._model, RuleBasedStanceModel)


def test_router_is_mounted_in_the_application() -> None:
    app = create_app(_settings())

    assert set(EXPECTED_ROUTES) <= set(app.openapi()["paths"])


async def test_readyz_is_red_when_embeddings_are_unreachable() -> None:
    app = create_app(_settings())
    app.state.db = StubDatabase()
    app.state.evidence_retrieval.readiness = StaticRetrievalReadiness(
        embeddings_reachable=False, reranker_reachable=True
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "NOT_READY"
    assert body["details"] == [
        {
            "message": "embedding provider unreachable",
            "field": "evidence_retrieval",
            "code": "unavailable",
        }
    ]


def test_retrieval_never_imports_corpus_infrastructure_or_tables() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        for name in imported_names(path):
            if name.startswith("evidence_corpus.infrastructure"):
                offenders.append(f"{path.name}: {name}")
        text = path.read_text(encoding="utf-8")
        if "evidence_corpus_indexed_passage" in text:
            offenders.append(f"{path.name}: corpus table name")

    assert offenders == []
