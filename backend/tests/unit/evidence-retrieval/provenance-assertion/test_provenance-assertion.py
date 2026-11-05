"""Contract freeze: a candidate without provenance blocks freezing."""

from __future__ import annotations

from tests.unit.evidence_retrieval_contract_helpers import field_names

from evidence_retrieval.domain.entities import EvidenceCandidate
from evidence_retrieval.domain.errors import CandidateWithoutProvenance
from evidence_retrieval.domain.evidence_pack import EvidencePack
from shared.errors import ValidationFailedError


def test_candidate_provenance_is_optional_at_construction_but_not_at_freeze() -> None:
    assert field_names(EvidenceCandidate) == [
        "passage_id",
        "stance",
        "score",
        "provenance",
    ]
    assert EvidenceCandidate.__annotations__["provenance"] is not None
    assert hasattr(EvidencePack, "assert_every_candidate_has_provenance")
    assert hasattr(EvidencePack, "freeze")


def test_candidate_without_provenance_is_a_validation_error_with_the_ids() -> None:
    error = CandidateWithoutProvenance(["psg_1", "psg_2"])

    assert isinstance(error, ValidationFailedError)
    assert error.code == "CANDIDATE_WITHOUT_PROVENANCE"
    assert error.status_code == 422
    assert error.passage_ids == ("psg_1", "psg_2")
    assert "psg_1" in error.message
