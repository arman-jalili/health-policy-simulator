"""Contract freeze: recording absence beside a contradiction is a stable conflict."""

from __future__ import annotations

from tests.unit.evidence_retrieval_contract_helpers import parameter_names

from evidence_retrieval.domain.errors import AbsenceWithContradiction
from evidence_retrieval.domain.evidence_pack import EvidencePack
from shared.errors import ConflictError


def test_absence_with_contradiction_is_a_conflict() -> None:
    error = AbsenceWithContradiction("evp_1")

    assert isinstance(error, ConflictError)
    assert error.code == "ABSENCE_WITH_CONTRADICTION"
    assert error.status_code == 409
    assert "evp_1" in error.message
    assert "absence" in error.message


def test_record_absence_keeps_the_truthfulness_guard_in_the_aggregate() -> None:
    assert parameter_names(EvidencePack.record_absence) == ["self", "queries", "reason"]
    assert "contradict" in (EvidencePack.record_absence.__doc__ or "").lower()
