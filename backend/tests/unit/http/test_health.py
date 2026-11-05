"""Health probes: liveness never depends on the database, readiness does."""

from __future__ import annotations

import httpx
from fastapi import FastAPI

from shared.app import create_app
from shared.config import Settings
from shared.enums import Persistence
from shared.http.middleware import REQUEST_ID_HEADER, TRACE_ID_HEADER
from tests.conftest import TEST_DATABASE_URL, StubDatabase


async def test_healthz_reports_ok_without_touching_the_database(
    client: httpx.AsyncClient, stub_database: StubDatabase
) -> None:
    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "health-policy-simulator",
        "version": "0.1.0",
    }
    assert stub_database.ping_count == 0


async def test_readyz_reports_ready_when_database_answers(
    client: httpx.AsyncClient, stub_database: StubDatabase
) -> None:
    response = await client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["checks"] == {
        "database": "ok",
        "llm": "not_configured",
        "evidence_retrieval": "ok",
        "evidence_retrieval_mode": "lexical+dense",
        "evidence_retrieval_detail": (
            "lexical+dense (hashing-char3gram-v1); reranker overlap-reranker-v1"
        ),
        "stakeholder_model": "ok",
        "stakeholder_institutions": "9",
        "claim_validation": "ok",
        "claim_validation_persistence": "memory",
        "simulation_orchestration": "ok",
        "simulation_orchestration_persistence": "memory",
        "simulation_model": "scripted-local",
    }
    assert response.headers["Cache-Control"] == "no-store"
    assert stub_database.ping_count == 1


async def test_readyz_returns_envelope_when_database_is_down(
    client: httpx.AsyncClient, failing_database: StubDatabase
) -> None:
    response = await client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "NOT_READY"
    assert body["message"] == "A required dependency is unavailable"
    assert body["details"] == [
        {"message": "connectivity check failed", "field": "database", "code": "unavailable"}
    ]
    assert body["trace_id"] == response.headers[REQUEST_ID_HEADER]
    assert response.headers["Retry-After"] == "5"


async def test_caller_supplied_trace_id_is_echoed(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz", headers={REQUEST_ID_HEADER: "req_caller_123"})

    assert response.headers[REQUEST_ID_HEADER] == "req_caller_123"
    assert response.headers[TRACE_ID_HEADER] == "req_caller_123"


async def test_invalid_trace_id_is_replaced(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz", headers={REQUEST_ID_HEADER: "short"})

    generated = response.headers[REQUEST_ID_HEADER]
    assert generated != "short"
    assert generated.startswith("req_")


async def test_metrics_exposes_prometheus_counters(client: httpx.AsyncClient) -> None:
    await client.get("/healthz")

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text
    assert 'method="GET"' in response.text


async def test_domain_event_counter_is_exposed(client: httpx.AsyncClient, app: FastAPI) -> None:
    from evidence_corpus.domain.events import PassageRevertedFromIndex

    await app.state.corpus.events.publish(
        [PassageRevertedFromIndex(passage_id="psg_1", reason="retraction")], actor="test"
    )

    response = await client.get("/metrics")

    assert 'domain_events_total{event="PassageRevertedFromIndex"} 1.0' in response.text


async def test_readyz_reports_an_unreachable_llm() -> None:
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        persistence=Persistence.MEMORY,
        llm_health_url="http://127.0.0.1:1/health",
    )
    app = create_app(settings)
    app.state.db = StubDatabase()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "NOT_READY"
    assert body["details"] == [
        {"message": "LLM health check failed", "field": "llm", "code": "unreachable"}
    ]


async def test_healthz_never_probes_the_llm() -> None:
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        persistence=Persistence.MEMORY,
        llm_health_url="http://127.0.0.1:1/health",
    )
    app = create_app(settings)
    stub = StubDatabase()
    app.state.db = stub
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert stub.ping_count == 0
