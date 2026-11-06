"""Integration: accepted, quarantined and failed batch outcomes stay distinct (#427, #434)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence
from tests.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.integration


def _write_pdf(path: Path, body: str) -> Path:
    import pymupdf

    document = pymupdf.open()  # type: ignore[no-untyped-call]
    page = document.new_page()
    page.insert_textbox(pymupdf.Rect(72, 72, 540, 760), body, fontsize=9)  # type: ignore[no-untyped-call]
    document.save(path)  # type: ignore[no-untyped-call]
    document.close()  # type: ignore[no-untyped-call]
    return path


def _app() -> FastAPI:
    return create_app(
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            persistence=Persistence.MEMORY,
            auth_mode=AuthMode.DEMO,
        )
    )


async def _run_batch(client: httpx.AsyncClient, paths: list[str]) -> dict[str, Any]:
    created = await client.post(
        "/api/v1/corpus/ingestion-runs",
        json={"shard_label": "batch", "paths": paths},
    )
    assert created.status_code == 202, created.text
    read = await client.get(f"/api/v1/corpus/ingestion-runs/{created.json()['run_id']}")
    assert read.status_code == 200, read.text
    payload = read.json()
    assert isinstance(payload, dict)
    return payload


async def test_accepted_quarantined_and_failed_paths_are_distinct(tmp_path: Path) -> None:
    good = _write_pdf(tmp_path / "good.pdf", "Die Kassenstellen werden aufgestockt. " * 40)
    thin = _write_pdf(tmp_path / "thin.pdf", "Kassenstellen")
    missing = tmp_path / "does-not-exist.pdf"
    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        payload = await _run_batch(client, [str(good), str(thin), str(missing)])
        thin_document = await client.post(
            "/api/v1/corpus/documents",
            json={
                "source_uri": str(thin),
                "publication": {
                    "outlet": "Test",
                    "published_on": "2020-01-01",
                    "medium": "print",
                },
                "source_type": "press_report",
            },
        )
        assert thin_document.status_code == 202, thin_document.text
        indexed = await client.post(
            f"/api/v1/corpus/documents/{thin_document.json()['document_id']}:index"
        )
    await app.state.db.dispose()

    outcomes = {item["path"]: item for item in payload["outcomes"]}
    assert outcomes[str(good)]["outcome"] == "accepted"
    assert outcomes[str(thin)]["outcome"] == "quarantined"
    assert "quality" in outcomes[str(thin)]["reason"]
    assert "< 0.85" in outcomes[str(thin)]["reason"]
    assert outcomes[str(missing)]["outcome"] == "failed"
    assert "ExtractionFailed" in outcomes[str(missing)]["reason"]
    assert (payload["accepted"], payload["quarantined"], payload["failed"]) == (1, 1, 1)

    assert indexed.status_code == 409, indexed.text
    assert indexed.json()["code"] == "DOCUMENT_NOT_CITABLE"
    assert indexed.json()["message"] == outcomes[str(thin)]["reason"].removeprefix(
        "DOCUMENT_NOT_CITABLE: "
    )


async def test_resuming_a_quarantined_path_reports_quarantined_again(tmp_path: Path) -> None:
    thin = _write_pdf(tmp_path / "thin-resume.pdf", "Kassenstellen")
    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        first = await _run_batch(client, [str(thin)])
        second = await _run_batch(client, [str(thin)])
    await app.state.db.dispose()

    assert first["quarantined"] == 1
    assert second["quarantined"] == 1
    assert second["failed"] == 0
    assert second["outcomes"][0]["reason"] == first["outcomes"][0]["reason"]


async def test_resuming_the_same_shard_is_idempotent(tmp_path: Path) -> None:
    good = _write_pdf(tmp_path / "resume.pdf", "Die Kassenstellen werden aufgestockt. " * 40)
    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        first = await _run_batch(client, [str(good)])
        second = await _run_batch(client, [str(good)])
    await app.state.db.dispose()

    assert first["accepted"] == 1
    assert second["accepted"] == 1
    assert second["failed"] == 0
    assert second["outcomes"][0]["outcome"] == "accepted"


@pytest.mark.skipif(
    __import__("shutil").which("tesseract") is not None,
    reason="OCR stack is installed; this test covers its absence",
)
async def test_scanned_batch_fails_fast_with_a_named_ocr_reason(tmp_path: Path) -> None:
    import pymupdf

    scanned = tmp_path / "scan.pdf"
    document = pymupdf.open()  # type: ignore[no-untyped-call]
    document.new_page()
    document.save(scanned)  # type: ignore[no-untyped-call]
    document.close()  # type: ignore[no-untyped-call]

    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        payload = await _run_batch(client, [str(scanned)])
        ready = (await client.get("/readyz")).json()
    await app.state.db.dispose()

    assert payload["status"] == "failed"
    assert payload["failed"] == 1
    assert payload["failure_reason"].startswith("OCR_UNAVAILABLE")
    assert payload["outcomes"][0]["reason"].startswith("OCR_UNAVAILABLE")
    assert ready["checks"]["ocr"] == "absent"
