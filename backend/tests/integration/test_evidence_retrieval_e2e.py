"""E2E: evidence retrieval is reachable through the public API."""

from __future__ import annotations

from datetime import UTC, date, datetime

import httpx

from evidence_corpus.domain.entities import CorpusSnapshot, IndexManifest
from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Offsets, SpeakerKind
from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence
from tests.conftest import TEST_DATABASE_URL


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        persistence=Persistence.MEMORY,
        auth_mode=AuthMode.DEMO,
    )


def _passage() -> PassageView:
    return PassageView(
        passage_id="psg_1",
        article_id="art_1",
        document_id="doc_1",
        text="Die Kassenstellen werden aufgestockt.",
        provenance=ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, 10),
            source_uri="s3://corpus/source.pdf",
        ),
        speaker_kind=SpeakerKind.INSTITUTION,
        citable=True,
    )


async def test_evidence_retrieval_runs_through_the_public_api() -> None:
    app = create_app(_settings())
    corpus = app.state.corpus
    manifest = await corpus.index_writer.upsert_passages("doc_1", [_passage()])
    snapshot = CorpusSnapshot.pin(
        label="e2e",
        document_ids=["doc_1"],
        index_manifest=IndexManifest(
            index_version=manifest.index_version,
            embedding_model=manifest.embedding_model,
            searchable_since=manifest.searchable_since,
            passage_count=manifest.passage_count,
        ),
        pinned_at=datetime.now(tz=UTC),
        manifest_hash="sha256:e2e",
    )
    await corpus.snapshots.save(snapshot)

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        candidates = await client.post(
            "/api/v1/evidence/candidates",
            json={
                "claim": "Kassenstellen",
                "claim_type": "quantitative",
                "snapshot_id": snapshot.id,
            },
        )
        assert candidates.status_code == 200, candidates.text
        assert [c["passage_id"] for c in candidates.json()["candidates"]] == ["psg_1"]

        packed = await client.post(
            "/api/v1/evidence/packs",
            json={
                "claim": "Kassenstellen",
                "claim_type": "quantitative",
                "snapshot_id": snapshot.id,
            },
        )
        assert packed.status_code == 201, packed.text
        body = packed.json()
        assert body["absence"] is not None
        assert body["candidates"][0]["passage_id"] == "psg_1"
        pack_id = body["pack_id"]

        read = await client.get(f"/api/v1/evidence/packs/{pack_id}")
        assert read.status_code == 200, read.text
        assert read.json()["pack_id"] == pack_id

        scores = await client.get(f"/api/v1/evidence/packs/{pack_id}/scores")
        assert scores.status_code == 200, scores.text
        assert scores.json()["candidates"][0]["passage_id"] == "psg_1"

        reweighted = await client.post(
            f"/api/v1/evidence/packs/{pack_id}/reweight",
            json={"policy": {"half_life_days": 30, "exempt_source_types": ["legislation"]}},
        )
        assert reweighted.status_code == 201, reweighted.text
        assert reweighted.json()["pack_id"] != pack_id
