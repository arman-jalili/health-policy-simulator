"""Reproducibility: the same claim + snapshot yields the same candidate ids."""

from __future__ import annotations

from datetime import UTC, date, datetime

from evidence_corpus.domain.published import (
    PassageView,
    ProvenanceView,
    SnapshotIndexView,
)
from evidence_corpus.domain.values import (
    AuthorityRule,
    ClaimType,
    Offsets,
    SpeakerKind,
    authority_rule,
)
from evidence_retrieval.application.commands import AssembleEvidencePackRequest
from evidence_retrieval.application.services import (
    AssembleEvidencePack,
    SearchEvidenceCandidates,
)
from evidence_retrieval.domain.services import (
    ReciprocalRankFusion,
    ScoreEvidenceCandidates,
)
from evidence_retrieval.domain.values import SnapshotId, StanceLabel
from evidence_retrieval.infrastructure.memory import InMemoryEvidencePackRepository
from evidence_retrieval.infrastructure.query_rewrite import GermanQueryRewrite


class Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 5, tzinfo=UTC)


class FixedSearch:
    def __init__(self, passages: list[PassageView]) -> None:
        self.passages = passages

    async def search(self, query: str, snapshot_id: SnapshotId, limit: int) -> list[PassageView]:
        return self.passages[:limit]

    async def authority_rule(self, claim_type: ClaimType) -> AuthorityRule:
        return authority_rule(claim_type)

    async def snapshot_index(self, snapshot_id: SnapshotId) -> SnapshotIndexView:
        return SnapshotIndexView(index_version="idx-test", embedding_model="none")

    async def dense_search(
        self, query: str, snapshot_id: SnapshotId, limit: int
    ) -> list[tuple[PassageView, float]]:
        return []


class FixedStance:
    async def classify(self, claim: str, passage: PassageView) -> StanceLabel:
        return (
            StanceLabel.CONTRADICTING
            if passage.passage_id == "psg_contra"
            else StanceLabel.SUPPORTING
        )


def _passage(passage_id: str, text: str) -> PassageView:
    return PassageView(
        passage_id=passage_id,
        article_id="art_1",
        document_id="doc_1",
        text=text,
        provenance=ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, 10),
            source_uri="s3://corpus/source.pdf",
        ),
        speaker_kind=SpeakerKind.INSTITUTION,
        citable=True,
    )


def _service() -> AssembleEvidencePack:
    search = FixedSearch(
        [
            _passage("psg_support", "Kassenstellen werden aufgestockt."),
            _passage("psg_contra", "Die Kassenstellen werden nicht aufgestockt."),
        ]
    )
    return AssembleEvidencePack(
        search_candidates=SearchEvidenceCandidates(
            search_port=search,
            query_rewrite=GermanQueryRewrite(),
            fusion=ReciprocalRankFusion(),
            stance_classifier=FixedStance(),  # type: ignore[arg-type]
            scorer=ScoreEvidenceCandidates(),
        ),
        packs=InMemoryEvidencePackRepository(),
        clock=Clock(),
    )


async def test_refreezing_the_same_claim_and_snapshot_keeps_candidate_ids() -> None:
    service = _service()
    request = AssembleEvidencePackRequest(
        claim="Kassenstellen",
        claim_type=ClaimType.QUANTITATIVE,
        snapshot_id="snap_1",
    )

    first = await service.execute(request)
    second = await service.execute(request)

    assert first.pack_id != second.pack_id
    assert [c.passage_id for c in first.candidates] == [c.passage_id for c in second.candidates]
    assert [c.passage_id for c in first.candidates] == ["psg_support", "psg_contra"]
    assert first.absence is None
