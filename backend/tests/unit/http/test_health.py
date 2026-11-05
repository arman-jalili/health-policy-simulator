"""Health probes: liveness never depends on the database, readiness does."""

from __future__ import annotations

import httpx

from shared.http.middleware import REQUEST_ID_HEADER, TRACE_ID_HEADER
from tests.conftest import StubDatabase


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
    assert response.json()["checks"] == {"database": "ok"}
    assert response.headers["Cache-Control"] == "no-store"
    assert stub_database.ping_count == 1


async def test_readyz_returns_envelope_when_database_is_down(
    client: httpx.AsyncClient, failing_database: StubDatabase
) -> None:
    response = await client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "NOT_READY"
    assert body["message"] == "Database is not reachable"
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
