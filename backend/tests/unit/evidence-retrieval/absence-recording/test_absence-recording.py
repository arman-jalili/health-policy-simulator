"""Contract freeze: absence is a truthful value object and an API-visible outcome."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from tests.unit.evidence_retrieval_contract_helpers import field_names, parameter_names

from evidence_retrieval.application.dto import (
    AbsenceResult,
    EvidencePackResult,
    TraceResult,
)
from evidence_retrieval.domain.entities import RetrievalTrace
from evidence_retrieval.domain.errors import PackFrozen
from evidence_retrieval.domain.events import EvidenceAbsenceRecorded
from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.values import (
    AbsenceFinding,
    ClaimText,
    PackId,
    QueryRewrite,
    SnapshotId,
)
from evidence_retrieval.interfaces.http.router import router
from shared.config import Settings
from shared.enums import AuthMode, Persistence


def test_absence_finding_names_queries_snapshot_and_reason() -> None:
    assert field_names(AbsenceFinding) == ["queries", "snapshot_id", "reason"]
    finding = AbsenceFinding(
        queries=("Kassenstellen", "Kassenstellen OR Kasse"),
        snapshot_id="snap_1",  # type: ignore[arg-type]
        reason="no contradicting passage above threshold",
    )

    assert finding.queries == ("Kassenstellen", "Kassenstellen OR Kasse")
    assert finding.reason.startswith("no contradicting")


def test_record_absence_has_no_candidate_padding_parameter() -> None:
    assert parameter_names(EvidencePack.record_absence) == ["self", "queries", "reason"]


def test_absence_event_carries_the_search_basis() -> None:
    assert field_names(EvidenceAbsenceRecorded) == [
        "pack_id",
        "queries",
        "snapshot_id",
        "reason",
    ]


def test_pack_api_can_return_an_absence_as_a_first_class_field() -> None:
    app = FastAPI()
    app.include_router(router)
    openapi = app.openapi()
    schema = openapi["components"]["schemas"]["EvidencePackResponse"]

    assert "absence" in schema["properties"]
    assert schema["properties"]["absence"]["anyOf"][0]["$ref"].endswith("AbsenceBody")


class _FakeAssemblePack:
    async def execute(self, request: Any) -> EvidencePackResult:
        return EvidencePackResult(
            pack_id="evp_1",
            claim=request.claim,
            snapshot_id=request.snapshot_id,
            index_version="idx-1",
            candidates=[],
            absence=AbsenceResult(
                queries=["Kassenstellen"],
                snapshot_id=request.snapshot_id,
                reason="no contradicting passage above threshold",
            ),
            trace=TraceResult(
                embedding_model="text-embedding-3-large",
                reranker_model="cross-encoder",
                query_rewrite="Kassenstellen",
                stance_counts={},
            ),
            frozen_at=datetime(2026, 11, 5, tzinfo=UTC),
        )


async def test_absence_returns_200_and_a_non_empty_absence_body() -> None:
    app = FastAPI()
    app.include_router(router)

    @asynccontextmanager
    async def transaction() -> AsyncIterator[None]:
        yield

    app.state.settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://hps:hps@localhost:5433/health_policy",
        persistence=Persistence.MEMORY,
        auth_mode=AuthMode.DEMO,
    )
    app.state.evidence_retrieval = SimpleNamespace(
        assemble_pack=_FakeAssemblePack(),
        transaction=transaction,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/evidence/packs",
            json={
                "claim": "Kassenstellen",
                "claim_type": "quantitative",
                "snapshot_id": "snap_1",
            },
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["absence"] is not None
    assert body["absence"]["queries"] == ["Kassenstellen"]
    assert body["absence"]["reason"].startswith("no contradicting")


def test_record_absence_after_freeze_is_refused_without_mutation() -> None:
    pack = EvidencePack(
        id=PackId("evp_1"),
        claim=ClaimText("Kassenstellen"),
        snapshot_id=SnapshotId("snap_1"),
        index_version="idx-1",
        trace=RetrievalTrace(
            embedding_model="text-embedding-3-large",
            reranker_model="cross-encoder",
            query_rewrite=QueryRewrite("Kassenstellen", "Kassenstellen"),
            stance_counts={},
        ),
    )
    pack.freeze()

    with pytest.raises(PackFrozen):
        pack.record_absence(["Kassenstellen"], "late")

    assert pack.absence is None
