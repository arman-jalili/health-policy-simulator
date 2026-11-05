"""Contract freeze: the HTTP surface of EvidenceCorpus (ADR-004).

All eight documented endpoints must appear in the generated OpenAPI document, declare their
required scope, and use the uniform error envelope. Handlers are deliberately not wired yet: until
the implementation issues land they answer `501` with a machine-readable code, which is itself part
of the contract (a freeze must not pretend to work).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from shared.http.middleware import REQUEST_ID_HEADER

ENDPOINTS: dict[str, set[str]] = {
    "/api/v1/corpus/documents": {"post"},
    "/api/v1/corpus/ingestion-runs": {"post"},
    "/api/v1/corpus/ingestion-runs/{run_id}": {"get"},
    "/api/v1/documents/{document_id}": {"get"},
    "/api/v1/passages/{passage_id}": {"get"},
    "/api/v1/corpus/snapshots": {"post"},
    "/api/v1/corpus/snapshots/{snapshot_id}": {"get"},
    "/api/v1/corpus/authority-rules": {"get"},
}

SCOPES: dict[str, str] = {
    "/api/v1/corpus/documents": "corpus:write",
    "/api/v1/corpus/ingestion-runs": "corpus:write",
    "/api/v1/corpus/ingestion-runs/{run_id}": "corpus:read",
    "/api/v1/documents/{document_id}": "corpus:read",
    "/api/v1/passages/{passage_id}": "corpus:read",
    "/api/v1/corpus/snapshots": "corpus:write",
    "/api/v1/corpus/snapshots/{snapshot_id}": "corpus:read",
    "/api/v1/corpus/authority-rules": "corpus:read",
}


@pytest.fixture
def openapi(app: FastAPI) -> dict[str, Any]:
    return app.openapi()


class TestEndpointInventory:
    def test_every_documented_endpoint_exists(self, openapi: dict[str, Any]) -> None:
        paths = openapi["paths"]
        assert isinstance(paths, dict)

        assert set(ENDPOINTS).issubset(paths)

    @pytest.mark.parametrize(("path", "methods"), ENDPOINTS.items())
    def test_methods_match_the_module_document(
        self, openapi: dict[str, Any], path: str, methods: set[str]
    ) -> None:
        paths = openapi["paths"]
        assert isinstance(paths, dict)
        operations = paths[path]
        assert isinstance(operations, dict)

        assert methods.issubset({method.lower() for method in operations})

    @pytest.mark.parametrize(("path", "scope"), SCOPES.items())
    def test_required_scope_is_declared(
        self, openapi: dict[str, Any], path: str, scope: str
    ) -> None:
        paths = openapi["paths"]
        assert isinstance(paths, dict)
        operations = paths[path]
        assert isinstance(operations, dict)

        for operation in operations.values():
            assert isinstance(operation, dict)
            assert operation.get("x-required-scope") == scope


class TestPayloadContracts:
    def test_ingest_returns_document_id_quality_and_citability(
        self, openapi: dict[str, Any]
    ) -> None:
        schema = _response_schema(openapi, "/api/v1/corpus/documents", "post", "202")

        assert {"document_id", "quality", "citable"} <= set(schema["properties"])

    def test_ingest_accepts_source_uri_publication_and_source_type(
        self, openapi: dict[str, Any]
    ) -> None:
        request_schema = _request_schema(openapi, "/api/v1/corpus/documents", "post")

        assert {"source_uri", "publication", "source_type"} <= set(request_schema["properties"])

    def test_passage_response_resolves_provenance(self, openapi: dict[str, Any]) -> None:
        schema = _response_schema(openapi, "/api/v1/passages/{passage_id}", "get", "200")

        assert {"text", "provenance", "speaker_kind", "citable"} <= set(schema["properties"])
        provenance = schema["properties"]["provenance"]
        assert isinstance(provenance, dict)

    def test_ingestion_run_reports_counts_and_status(self, openapi: dict[str, Any]) -> None:
        schema = _response_schema(openapi, "/api/v1/corpus/ingestion-runs/{run_id}", "get", "200")

        assert {"attempted", "accepted", "quarantined", "failed", "status"} <= set(
            schema["properties"]
        )

    def test_snapshot_creation_answers_201_with_manifest_hash(
        self, openapi: dict[str, Any]
    ) -> None:
        schema = _response_schema(openapi, "/api/v1/corpus/snapshots", "post", "201")

        assert {"snapshot_id", "manifest_hash"} <= set(schema["properties"])

    def test_authority_rules_returns_ordering_per_claim_type(self, openapi: dict[str, Any]) -> None:
        paths = openapi["paths"]
        assert isinstance(paths, dict)
        schema = _response_schema(openapi, "/api/v1/corpus/authority-rules", "get", "200")
        item = _resolve(openapi, schema["items"])

        assert {"claim_type", "ordered_tiers"} <= set(item["properties"])


class TestErrorEnvelope:
    async def test_unwired_endpoint_answers_501_with_the_envelope(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/api/v1/corpus/authority-rules")

        assert response.status_code == 501
        body = response.json()
        assert set(body) == {"code", "message", "details", "trace_id"}
        assert body["code"] == "ENDPOINT_NOT_IMPLEMENTED"
        assert body["trace_id"] == response.headers[REQUEST_ID_HEADER]

    async def test_unknown_document_returns_the_same_envelope_shape(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/api/v1/documents/doc_doesnotexist")

        assert response.status_code in {404, 501}
        assert set(response.json()) == {"code", "message", "details", "trace_id"}

    def test_documented_error_responses_are_declared(self, openapi: dict[str, Any]) -> None:
        paths = openapi["paths"]
        assert isinstance(paths, dict)
        operations = paths["/api/v1/corpus/documents"]["post"]

        assert {"401", "403", "422", "503"} <= set(operations["responses"])


def _operation(openapi: dict[str, Any], path: str, method: str) -> dict[str, Any]:
    paths = openapi["paths"]
    assert isinstance(paths, dict)
    operation = paths[path][method]
    assert isinstance(operation, dict)
    return operation


def _resolve(openapi: dict[str, Any], schema: object) -> dict[str, Any]:
    """Follow a `$ref` into components so assertions can read `properties`."""
    assert isinstance(schema, dict)
    ref = schema.get("$ref")
    if not ref:
        return schema
    name = ref.rsplit("/", 1)[-1]
    components = openapi["components"]
    assert isinstance(components, dict)
    resolved = components["schemas"][name]
    assert isinstance(resolved, dict)
    return resolved


def _response_schema(
    openapi: dict[str, Any], path: str, method: str, status: str
) -> dict[str, Any]:
    operation = _operation(openapi, path, method)
    schema = operation["responses"][status]["content"]["application/json"]["schema"]
    return _resolve(openapi, schema)


def _request_schema(openapi: dict[str, Any], path: str, method: str) -> dict[str, Any]:
    operation = _operation(openapi, path, method)
    return _resolve(openapi, operation["requestBody"]["content"]["application/json"]["schema"])
