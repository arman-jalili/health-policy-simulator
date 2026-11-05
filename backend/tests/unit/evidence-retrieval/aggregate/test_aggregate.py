"""Contract freeze: the EvidencePack aggregate boundary and method surface."""

from __future__ import annotations

import inspect
from datetime import date

import pytest
from tests.unit.evidence_retrieval_contract_helpers import field_names, parameter_names

from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import Offsets
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.errors import (
    AbsenceWithContradiction,
    CandidateWithoutProvenance,
    PackFrozen,
)
from evidence_retrieval.domain.events import EvidencePackAssembled
from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.values import (
    AbsenceFinding,
    ClaimText,
    EvidenceScore,
    PackId,
    PassageId,
    QueryRewrite,
    SnapshotId,
    StanceLabel,
)


def test_pack_fields_are_frozen() -> None:
    assert field_names(EvidencePack) == [
        "id",
        "claim",
        "snapshot_id",
        "index_version",
        "trace",
        "candidates",
        "absence",
        "frozen",
        "frozen_at",
        "events",
    ]


def test_pack_is_an_aggregate_not_a_value_object() -> None:
    pack = EvidencePack(
        id=PackId("evp_1"),
        claim=ClaimText("Kassenstellen"),
        snapshot_id=SnapshotId("snap_1"),
        index_version="idx-1",
        trace=RetrievalTrace(
            embedding_model="text-embedding-3-large",
            reranker_model="cross-encoder",
            query_rewrite=QueryRewrite(original="Kassenstellen", expanded="Kassenstellen"),
            stance_counts={},
        ),
    )

    assert pack.candidates == []
    assert pack.absence is None
    assert pack.frozen is False
    assert pack.events == []


def test_add_candidate_accepts_one_candidate() -> None:
    assert parameter_names(EvidencePack.add_candidate) == ["self", "candidate"]
    candidate = inspect.signature(EvidencePack.add_candidate).parameters["candidate"]
    assert candidate.annotation is not None
    assert EvidenceCandidate.__name__ == "EvidenceCandidate"


def test_record_absence_names_queries_and_reason() -> None:
    assert parameter_names(EvidencePack.record_absence) == ["self", "queries", "reason"]
    assert AbsenceFinding.__name__ == "AbsenceFinding"


def test_freeze_and_provenance_assertion_are_separate_steps() -> None:
    assert parameter_names(EvidencePack.freeze) == ["self"]
    assert parameter_names(EvidencePack.assert_every_candidate_has_provenance) == ["self"]


def test_pack_records_the_index_version_and_trace_for_reproducibility() -> None:
    fields = field_names(EvidencePack)

    assert "index_version" in fields
    assert "trace" in fields
    assert field_names(RetrievalTrace) == [
        "embedding_model",
        "reranker_model",
        "query_rewrite",
        "stance_counts",
        "retrieval_mode",
        "index_version",
    ]


def _score() -> EvidenceScore:
    return EvidenceScore(
        authority=0.8,
        lexical=0.7,
        semantic=0.6,
        recency=1.0,
        directness=0.5,
        final=3.6,
    )


def _provenance() -> ProvenanceView:
    return ProvenanceView(
        outlet="Der Standard",
        published_on=date(2026, 10, 1),
        medium="print",
        page_from=1,
        page_to=1,
        offsets=Offsets(0, 10),
        source_uri="s3://corpus/source.pdf",
    )


def _pack() -> EvidencePack:
    return EvidencePack(
        id=PackId("evp_1"),
        claim=ClaimText("Kassenstellen"),
        snapshot_id=SnapshotId("snap_1"),
        index_version="idx-1",
        trace=RetrievalTrace(
            embedding_model="text-embedding-3-large",
            reranker_model="cross-encoder",
            query_rewrite=QueryRewrite(original="Kassenstellen", expanded="Kassenstellen"),
            stance_counts={},
        ),
    )


def _candidate(
    passage_id: str = "psg_1",
    stance: StanceLabel = StanceLabel.SUPPORTING,
    with_provenance: bool = True,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        passage_id=PassageId(passage_id),
        stance=stance,
        score=_score(),
        provenance=_provenance() if with_provenance else None,
    )


def test_freeze_makes_the_pack_immutable_and_emits_the_assembled_event() -> None:
    pack = _pack()
    pack.add_candidate(_candidate())

    pack.freeze()

    assert pack.frozen is True
    assert pack.frozen_at is not None
    assert isinstance(pack.events[-1], EvidencePackAssembled)
    with pytest.raises(PackFrozen):
        pack.add_candidate(_candidate("psg_2"))


def test_add_after_freeze_leaves_the_pack_unchanged() -> None:
    pack = _pack()
    pack.add_candidate(_candidate())
    pack.freeze()
    before = list(pack.candidates)

    with pytest.raises(PackFrozen):
        pack.add_candidate(_candidate("psg_2"))

    assert pack.candidates == before


def test_record_absence_is_truthful_and_contradiction_blocks_it() -> None:
    pack = _pack()
    pack.record_absence(["Kassenstellen"], "no contradicting passage above threshold")

    assert pack.absence is not None
    assert pack.absence.queries == ("Kassenstellen",)
    contradictory = _pack()
    contradictory.add_candidate(_candidate(stance=StanceLabel.CONTRADICTING))
    with pytest.raises(AbsenceWithContradiction):
        contradictory.record_absence(["Kassenstellen"], "wrong")


def test_freeze_without_provenance_blocks_and_keeps_the_pack_open() -> None:
    pack = _pack()
    pack.add_candidate(_candidate(with_provenance=False))

    with pytest.raises(CandidateWithoutProvenance) as error:
        pack.freeze()

    assert error.value.passage_ids == ("psg_1",)
    assert pack.frozen is False
    assert pack.frozen_at is None


def test_candidate_ids_are_stable_for_the_same_search_result() -> None:
    first = _pack()
    second = _pack()
    for pack in (first, second):
        pack.add_candidate(_candidate("psg_1"))
        pack.add_candidate(_candidate("psg_2"))

    first.freeze()
    second.freeze()

    assert first.candidate_ids == second.candidate_ids == ("psg_1", "psg_2")
