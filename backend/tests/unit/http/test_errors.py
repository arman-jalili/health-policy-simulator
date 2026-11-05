"""Error envelope: every failure mode renders ``{code, message, details, trace_id}``."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.errors import AppError, ForbiddenError
from shared.http.middleware import REQUEST_ID_HEADER


@pytest.fixture
def app_with_failures(app: FastAPI) -> FastAPI:
    @app.get("/refuse")
    async def refuse() -> None:
        raise ForbiddenError("Missing scope corpus:write", code="SCOPE_MISSING")

    @app.get("/gone")
    async def gone() -> None:
        raise StarletteHTTPException(status_code=410, detail="run was deleted")

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("kaboom: internal detail")

    @app.get("/number")
    async def number(value: int) -> dict[str, int]:
        return {"value": value}

    @app.get("/domain-rule")
    async def domain_rule() -> None:
        raise AppError(
            "A position cannot change without a cited argument",
            code="POSITION_REVISION_REJECTED",
            status_code=409,
        )

    return app


async def test_unknown_route_returns_envelope(client: httpx.AsyncClient) -> None:
    response = await client.get("/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["details"] == []
    assert body["trace_id"] == response.headers[REQUEST_ID_HEADER]


async def test_app_error_keeps_domain_code(
    client: httpx.AsyncClient, app_with_failures: FastAPI
) -> None:
    response = await client.get("/refuse")

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "SCOPE_MISSING"
    assert body["message"] == "Missing scope corpus:write"


async def test_domain_conflict_maps_to_409(
    client: httpx.AsyncClient, app_with_failures: FastAPI
) -> None:
    response = await client.get("/domain-rule")

    assert response.status_code == 409
    assert response.json()["code"] == "POSITION_REVISION_REJECTED"


async def test_unmapped_http_status_falls_back_to_http_code(
    client: httpx.AsyncClient, app_with_failures: FastAPI
) -> None:
    response = await client.get("/gone")

    assert response.status_code == 410
    body = response.json()
    assert body["code"] == "HTTP_410"
    assert body["message"] == "run was deleted"


async def test_request_validation_reports_field(
    client: httpx.AsyncClient, app_with_failures: FastAPI
) -> None:
    response = await client.get("/number", params={"value": "not-a-number"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert body["details"][0]["field"] == "value"
    assert body["details"][0]["code"] == "int_parsing"


async def test_unexpected_error_hides_internals_and_keeps_trace_id(
    client: httpx.AsyncClient, app_with_failures: FastAPI
) -> None:
    response = await client.get("/crash", headers={REQUEST_ID_HEADER: "req_crash_trace"})

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["message"] == "Unexpected error"
    assert "kaboom" not in response.text
    assert body["trace_id"] == "req_crash_trace"
