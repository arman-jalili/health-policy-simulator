"""Behavioural gate: evidence scores are derived, not constants.

This test fails on the pre-fix code: every candidate shared ``(1, 1, 1, 1)`` and authority was
hardcoded to ``OTHER``. It exercises the public HTTP path against a seeded in-memory corpus.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from typing import Any

import httpx

from evidence_corpus.domain.entities import CorpusSnapshot, IndexManifest
from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Offsets, SourceType, SpeakerKind
from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence
from tests.conftest import TEST_DATABASE_URL, StubDatabase


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        persistence=Persistence.MEMORY,
        auth_mode=AuthMode.DEMO,
    )


def _passage(
    passage_id: str,
    *,
    text: str,
    source_type: SourceType,
    published_on: date,
) -> PassageView:
    return PassageView(
        passage_id=passage_id,
        article_id="art_1",
        document_id="doc_1",
        text=text,
        provenance=ProvenanceView(
            outlet="Testausgabe",
            published_on=published_on,
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, len(text)),
            source_uri="s3://corpus/source.pdf",
        ),
        speaker_kind=SpeakerKind.INSTITUTION,
        citable=True,
        source_type=source_type,
    )


async def _seed_corpus(app: Any) -> tuple[str, str]:
    corpus = app.state.corpus
    passages = [
        _passage(
            "psg_statute",
            text="Kassenstellen werden aufgestockt.",
            source_type=SourceType.LEGISLATION,
            published_on=date(1995, 1, 1),
        ),
        _passage(
            "psg_press",
            text="Kassenstellen werden aufgestockt.",
            source_type=SourceType.PRESS_REPORT,
            published_on=date(1995, 1, 1),
        ),
        _passage(
            "psg_context",
            text="Die Kassenstellen sind umstritten.",
            source_type=SourceType.INSTITUTIONAL_STATEMENT,
            published_on=date(2026, 10, 1),
        ),
    ]
    manifest = await corpus.index_writer.upsert_passages("doc_1", passages)
    snapshot = CorpusSnapshot.pin(
        label="score-derivation",
        document_ids=["doc_1"],
        index_manifest=IndexManifest(
            index_version="idx-score",
            embedding_model=manifest.embedding_model,
            searchable_since=manifest.searchable_since,
            passage_count=manifest.passage_count,
        ),
        pinned_at=datetime.now(tz=UTC),
        manifest_hash="sha256:score",
    )
    await corpus.snapshots.save(snapshot)
    return snapshot.id, "idx-score"


def _by_id(candidates: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(candidate["passage_id"]): candidate for candidate in candidates}


async def test_scores_are_derived_from_each_candidate_and_trace_is_truthful() -> None:
    app = create_app(_settings())
    app.state.db = StubDatabase()
    snapshot_id, index_version = await _seed_corpus(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/evidence/candidates",
            json={
                "claim": "Kassenstellen werden aufgestockt",
                "claim_type": "legal",
                "snapshot_id": snapshot_id,
            },
        )
        assert response.status_code == 200, response.text
        candidates = _by_id(response.json()["candidates"])

        # The bug: all five component vectors were identical. At least two must differ.
        component_vectors = {
            (
                candidate["score"]["authority"],  # type: ignore[index]
                candidate["score"]["lexical"],  # type: ignore[index]
                candidate["score"]["semantic"],  # type: ignore[index]
                candidate["score"]["recency"],  # type: ignore[index]
                candidate["score"]["directness"],  # type: ignore[index]
            )
            for candidate in candidates.values()
        }
        assert len(component_vectors) >= 2

        # Authority is per source type from the corpus rule, not AuthorityTier.OTHER.
        assert candidates["psg_statute"]["score"]["authority"] == 1.0  # type: ignore[index]
        assert candidates["psg_context"]["score"]["authority"] == 0.5  # type: ignore[index]
        assert math.isclose(
            candidates["psg_press"]["score"]["authority"],  # type: ignore[index]
            1 / 3,
            rel_tol=0.0,
            abs_tol=1e-9,
        )

        # A 1995 statute keeps full recency weight; a 1995 press report does not.
        assert candidates["psg_statute"]["score"]["recency"] == 1.0  # type: ignore[index]
        assert candidates["psg_press"]["score"]["recency"] < 0.01  # type: ignore[index]
        assert candidates["psg_context"]["score"]["directness"] < 1.0  # type: ignore[index]
        assert candidates["psg_statute"]["score"]["directness"] == 1.0  # type: ignore[index]

        # The dense branch is real: at least one candidate carries a vector similarity, and
        # every semantic component stays a bounded measurement rather than a constant.
        assert any(
            candidate["score"]["semantic"] > 0.0  # type: ignore[index]
            for candidate in candidates.values()
        )
        assert all(
            0.0 <= candidate["score"]["semantic"] <= 1.0  # type: ignore[index]
            for candidate in candidates.values()
        )

        packed = await client.post(
            "/api/v1/evidence/packs",
            json={
                "claim": "Kassenstellen werden aufgestockt",
                "claim_type": "legal",
                "snapshot_id": snapshot_id,
            },
        )
        assert packed.status_code == 201, packed.text
        trace = packed.json()["trace"]
        assert trace["retrieval_mode"] == "lexical+dense"
        assert trace["embedding_model"] == "hashing-char3gram-v1"
        assert trace["reranker_model"] == "overlap-reranker-v1"
        assert trace["index_version"] == index_version
        assert packed.json()["index_version"] == index_version

        ready = await client.get("/readyz")
        assert ready.status_code == 200, ready.text
        checks = ready.json()["checks"]
        assert checks["evidence_retrieval_mode"] == "lexical+dense"
        assert "hashing-char3gram-v1" in checks["evidence_retrieval_detail"]
