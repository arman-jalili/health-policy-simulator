"""Contract freeze: recording absence beside a contradiction is a stable conflict."""

from __future__ import annotations

from datetime import date

import pytest
from tests.unit.evidence_retrieval_contract_helpers import parameter_names

from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import Offsets
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.errors import AbsenceWithContradiction
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


def test_failed_absence_recording_leaves_absence_and_events_unchanged() -> None:
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
    pack.add_candidate(
        EvidenceCandidate(
            passage_id=PassageId("psg_1"),
            stance=StanceLabel.CONTRADICTING,
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
    )
    events_before = list(pack.events)

    with pytest.raises(AbsenceWithContradiction):
        pack.record_absence(["Kassenstellen"], "wrong")

    assert pack.absence is None
    assert pack.events == events_before
