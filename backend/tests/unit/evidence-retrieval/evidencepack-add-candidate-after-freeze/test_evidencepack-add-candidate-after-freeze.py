"""Contract freeze: a frozen pack refuses new candidates with a stable error."""

from __future__ import annotations

import inspect

from tests.unit.evidence_retrieval_contract_helpers import parameter_names

from evidence_retrieval.domain.errors import PackFrozen
from evidence_retrieval.domain.evidence_pack import EvidencePack
from shared.errors import ConflictError


def test_pack_frozen_is_a_conflict_with_a_stable_code() -> None:
    error = PackFrozen("evp_1")

    assert isinstance(error, ConflictError)
    assert error.code == "PACK_FROZEN"
    assert error.status_code == 409
    assert "evp_1" in error.message


def test_add_candidate_is_the_only_entry_point_and_is_guarded_by_freeze() -> None:
    assert parameter_names(EvidencePack.add_candidate) == ["self", "candidate"]
    assert inspect.getsource(EvidencePack.add_candidate).find("frozen") >= 0
    assert "frozen" in EvidencePack.__annotations__


def test_pack_exposes_the_frozen_flag_and_timestamp() -> None:
    assert "frozen" in EvidencePack.__annotations__
    assert "frozen_at" in EvidencePack.__annotations__
