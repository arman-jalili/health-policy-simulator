"""Contract freeze: the HTTP surface of EvidenceCorpus (ADR-004).

All eight documented endpoints must appear in the generated OpenAPI document, declare their
required scope, and use the uniform error envelope. Handlers are deliberately not wired yet: until
the implementation issues land they answer `501` with a machine-readable code, which is itself part
of the contract (a freeze must not pretend to work).
"""

from __future__ import annotations

from pathlib import Path
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
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/corpus/ingestion-runs/run_missing",
            "/api/v1/documents/doc_missing",
            "/api/v1/passages/psg_missing",
            "/api/v1/corpus/snapshots/snp_missing",
        ],
    )
    async def test_read_endpoints_are_wired(self, client: httpx.AsyncClient, path: str) -> None:
        """No documented read route may still answer 501 after the API contract issue."""
        response = await client.get(path)

        assert response.status_code != 501
        assert "code" in response.json()

    async def test_error_envelope_carries_the_request_trace_id(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/api/v1/passages/psg_missing")

        assert response.status_code == 404
        body = response.json()
        assert set(body) == {"code", "message", "details", "trace_id"}
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


class TestWiredEndpoints:
    """End-to-end behaviour of the corpus API after wiring (AC 12)."""

    async def test_ingest_reports_quality_and_citability(
        self, client: httpx.AsyncClient, tmp_path: Path
    ) -> None:
        import pymupdf

        path = tmp_path / "press.pdf"
        document = pymupdf.open()  # type: ignore[no-untyped-call]
        page = document.new_page()
        page.insert_textbox(
            pymupdf.Rect(72, 72, 540, 760),  # type: ignore[no-untyped-call]
            "Die Kassenstellen werden aufgestockt. " * 40,
            fontsize=9,
        )
        document.save(path)  # type: ignore[no-untyped-call]
        document.close()  # type: ignore[no-untyped-call]

        response = await client.post(
            "/api/v1/corpus/documents",
            json={
                "source_uri": str(path),
                "publication": {
                    "outlet": "Der Standard",
                    "published_on": "2026-10-01",
                    "medium": "print",
                },
                "source_type": "press_report",
            },
        )

        assert response.status_code == 202
        body = response.json()
        assert body["document_id"].startswith("doc_")
        assert body["quality"]["method"] == "native"
        assert body["citable"] is True

    async def test_ingestion_run_round_trip(self, client: httpx.AsyncClient) -> None:
        created = await client.post(
            "/api/v1/corpus/ingestion-runs",
            json={"shard_label": "shard-1", "paths": ["/corpus/a.pdf"]},
        )

        assert created.status_code == 202
        run_id = created.json()["run_id"]

        read = await client.get(f"/api/v1/corpus/ingestion-runs/{run_id}")

        assert read.status_code == 200
        assert read.json()["status"] == "running"
        assert read.json()["attempted"] == 0

    async def test_unknown_ingestion_run_uses_the_error_envelope(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/api/v1/corpus/ingestion-runs/run_missing")

        assert response.status_code == 404
        assert response.json()["code"] == "RUN_NOT_FOUND"

    async def test_authority_rules_are_claim_type_relative(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/corpus/authority-rules")

        assert response.status_code == 200
        rules = response.json()
        assert {rule["claim_type"] for rule in rules} == {
            "quantitative",
            "legal",
            "causal",
            "qualitative",
        }
        legal = next(rule for rule in rules if rule["claim_type"] == "legal")
        assert legal["ordered_tiers"].index("legislation") < legal["ordered_tiers"].index(
            "press_report"
        )

    async def test_single_claim_type_filter(self, client: httpx.AsyncClient) -> None:
        response = await client.get(
            "/api/v1/corpus/authority-rules", params={"claim_type": "quantitative"}
        )

        assert response.status_code == 200
        assert [rule["claim_type"] for rule in response.json()] == ["quantitative"]

    async def test_document_endpoint_returns_the_ingested_document(
        self, client: httpx.AsyncClient, tmp_path: Path
    ) -> None:
        import pymupdf

        path = tmp_path / "legal.pdf"
        document = pymupdf.open()  # type: ignore[no-untyped-call]
        page = document.new_page()
        page.insert_textbox(
            pymupdf.Rect(72, 72, 540, 760),  # type: ignore[no-untyped-call]
            "§ 1 Kassenstellen werden aufgestockt. " * 40,
            fontsize=9,
        )
        document.save(path)  # type: ignore[no-untyped-call]
        document.close()  # type: ignore[no-untyped-call]

        ingested = await client.post(
            "/api/v1/corpus/documents",
            json={
                "source_uri": str(path),
                "publication": {
                    "outlet": "BGBl",
                    "published_on": "2026-10-01",
                    "medium": "print",
                },
                "source_type": "legislation",
            },
        )
        document_id = ingested.json()["document_id"]

        read = await client.get(f"/api/v1/documents/{document_id}")

        assert read.status_code == 200
        body = read.json()
        assert body["document_id"] == document_id
        assert body["source_type"] == "legislation"
        assert body["citable"] is True
