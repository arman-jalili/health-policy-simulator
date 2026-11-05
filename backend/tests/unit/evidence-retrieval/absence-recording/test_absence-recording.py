"""Contract freeze: absence is a truthful value object and an API-visible outcome."""

from __future__ import annotations

from fastapi import FastAPI
from tests.unit.evidence_retrieval_contract_helpers import field_names, parameter_names

from evidence_retrieval.domain.events import EvidenceAbsenceRecorded
from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.values import AbsenceFinding
from evidence_retrieval.interfaces.http.router import router


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
