"""Contract freeze: a candidate without provenance blocks freezing."""

from __future__ import annotations

from datetime import date

import pytest
from tests.unit.evidence_retrieval_contract_helpers import field_names

from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import Offsets
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.errors import CandidateWithoutProvenance
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


def _candidate(passage_id: str, with_provenance: bool) -> EvidenceCandidate:
    provenance = (
        ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, 10),
            source_uri="s3://corpus/source.pdf",
        )
        if with_provenance
        else None
    )
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
        provenance=provenance,
    )


def test_freeze_reports_every_missing_passage_and_emits_no_event() -> None:
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
    pack.add_candidate(_candidate("psg_1", with_provenance=False))
    pack.add_candidate(_candidate("psg_2", with_provenance=True))
    pack.add_candidate(_candidate("psg_3", with_provenance=False))

    with pytest.raises(CandidateWithoutProvenance) as error:
        pack.freeze()

    assert error.value.passage_ids == ("psg_1", "psg_3")
    assert pack.events == []
    assert pack.frozen is False
