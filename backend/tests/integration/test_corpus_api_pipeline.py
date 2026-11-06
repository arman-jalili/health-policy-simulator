"""Integration: the public corpus API can reach a searchable, citable passage (#424)."""

from __future__ import annotations

from pathlib import Path

import httpx

from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence
from tests.conftest import TEST_DATABASE_URL

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "demo-corpus.pdf"


async def test_api_only_document_segment_index_snapshot_and_pack() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            persistence=Persistence.MEMORY,
            auth_mode=AuthMode.DEMO,
        )
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        ingested = await client.post(
            "/api/v1/corpus/documents",
            json={
                "source_uri": str(SAMPLE),
                "publication": {
                    "outlet": "Demo Corpus",
                    "published_on": "2026-01-01",
                    "medium": "print",
                },
                "source_type": "official_statistics",
            },
        )
        assert ingested.status_code == 202, ingested.text
        assert ingested.json()["citable"] is False
        document_id = ingested.json()["document_id"]

        segmented = await client.post(f"/api/v1/corpus/documents/{document_id}:segment")
        assert segmented.status_code == 200, segmented.text
        assert segmented.json()["article_count"] > 0
        assert segmented.json()["citable"] is True

        indexed = await client.post(f"/api/v1/corpus/documents/{document_id}:index")
        assert indexed.status_code == 200, indexed.text
        assert indexed.json()["citable"] is True
        assert indexed.json()["passage_count"] > 0

        snapshot = await client.post(
            "/api/v1/corpus/snapshots",
            json={"label": "api-pipeline", "document_ids": [document_id]},
        )
        assert snapshot.status_code == 201, snapshot.text
        snapshot_id = snapshot.json()["snapshot_id"]

        packed = await client.post(
            "/api/v1/evidence/packs",
            json={
                "claim": "Kassenstellen",
                "claim_type": "qualitative",
                "snapshot_id": snapshot_id,
            },
        )
        assert packed.status_code == 201, packed.text
        assert packed.json()["candidates"]
    await app.state.db.dispose()
