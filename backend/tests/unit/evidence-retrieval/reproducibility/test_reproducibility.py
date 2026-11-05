"""Contract freeze: a pack names the snapshot, index version and models that produced it."""

from __future__ import annotations

from fastapi import FastAPI
from tests.unit.evidence_retrieval_contract_helpers import (
    field_names,
    parameter_names,
)

from evidence_retrieval.domain.events import EvidencePackAssembled
from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.repositories import EvidencePackRepository
from evidence_retrieval.interfaces.http.router import router


def test_pack_carries_the_reproducibility_inputs() -> None:
    fields = field_names(EvidencePack)

    assert "claim" in fields
    assert "snapshot_id" in fields
    assert "index_version" in fields
    assert "trace" in fields


def test_trace_names_both_models_and_the_rewrite() -> None:
    from evidence_retrieval.domain.entities import RetrievalTrace

    assert field_names(RetrievalTrace) == [
        "embedding_model",
        "reranker_model",
        "query_rewrite",
        "stance_counts",
    ]


def test_repository_can_find_the_latest_pack_for_a_claim() -> None:
    assert parameter_names(EvidencePackRepository.latest_for_claim) == ["self", "claim"]


def test_assembled_event_publishes_the_index_version() -> None:
    assert field_names(EvidencePackAssembled) == [
        "pack_id",
        "claim_hash",
        "candidate_count",
        "has_absence",
        "index_version",
    ]


def test_assembling_the_same_claim_against_the_same_snapshot_is_a_defined_operation() -> None:
    app = FastAPI()
    app.include_router(router)
    operation = app.openapi()["paths"]["/api/v1/evidence/packs"]["post"]

    assert operation["x-required-scope"] == "runs:write"
    assert operation["responses"]["201"]["description"]
