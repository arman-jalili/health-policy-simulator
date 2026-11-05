"""Contract freeze: a frozen pack refuses new candidates with a stable error."""

from __future__ import annotations

import inspect
from datetime import date

import pytest
from tests.unit.evidence_retrieval_contract_helpers import parameter_names

from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import Offsets
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.errors import PackFrozen
from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.values import (
    ClaimText,
    EvidenceScore,
    PackId,
    PassageId,
    QueryRewrite,
    SnapshotId,
    StanceLabel,
)
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


def _pack() -> EvidencePack:
    return EvidencePack(
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


def _candidate(passage_id: str) -> EvidenceCandidate:
    return EvidenceCandidate(
        passage_id=PassageId(passage_id),
        stance=StanceLabel.SUPPORTING,
        score=EvidenceScore(
            authority=0.8,
            lexical=0.7,
            semantic=0.6,
            recency=1.0,
            directness=0.5,
            final=3.6,
        ),
        provenance=ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, 10),
            source_uri="s3://corpus/source.pdf",
        ),
    )


def test_rejected_candidate_does_not_change_any_pack_state() -> None:
    pack = _pack()
    pack.add_candidate(_candidate("psg_1"))
    pack.freeze()
    candidates_before = list(pack.candidates)
    events_before = list(pack.events)
    frozen_at_before = pack.frozen_at

    with pytest.raises(PackFrozen):
        pack.add_candidate(_candidate("psg_2"))

    assert pack.candidates == candidates_before
    assert pack.events == events_before
    assert pack.frozen_at == frozen_at_before
