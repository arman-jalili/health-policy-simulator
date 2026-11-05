"""Hybrid search: a German compound query finds hits a naive term query misses."""

from __future__ import annotations

from datetime import date

import pytest

from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import (
    AuthorityRule,
    ClaimType,
    Offsets,
    SpeakerKind,
    authority_rule,
)
from evidence_retrieval.application.commands import SearchEvidenceCandidatesRequest
from evidence_retrieval.application.services import SearchEvidenceCandidates
from evidence_retrieval.domain.services import (
    ReciprocalRankFusion,
    ScoreEvidenceCandidates,
)
from evidence_retrieval.domain.values import SnapshotId, StanceLabel
from evidence_retrieval.infrastructure.query_rewrite import GermanQueryRewrite


class FakePassageSearch:
    def __init__(self, passages: list[PassageView]) -> None:
        self.passages = passages

    async def search(self, query: str, snapshot_id: SnapshotId, limit: int) -> list[PassageView]:
        terms = [term.strip().casefold() for term in query.split(" OR ")]
        hits = [
            passage
            for passage in self.passages
            if any(term in passage.text.casefold() for term in terms)
        ]
        return hits[:limit]

    async def authority_rule(self, claim_type: ClaimType) -> AuthorityRule:
        return authority_rule(claim_type)


class FakeStanceClassifier:
    async def classify(self, claim: str, passage: PassageView) -> StanceLabel:
        return StanceLabel.SUPPORTING


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


@pytest.mark.asyncio
async def test_compound_query_returns_hits_that_a_naive_term_query_misses() -> None:
    compound = _passage("psg_compound", "Die Kassenstellen werden aufgestockt.")
    parts = _passage("psg_parts", "Die Kasse wird aufgestockt.")
    search = FakePassageSearch([compound, parts])

    naive = await search.search("Kassenstellen", SnapshotId("snap_1"), limit=10)
    assert [passage.passage_id for passage in naive] == ["psg_compound"]

    service = SearchEvidenceCandidates(
        search_port=search,
        query_rewrite=GermanQueryRewrite(),
        fusion=ReciprocalRankFusion(),
        stance_classifier=FakeStanceClassifier(),  # type: ignore[arg-type]
        scorer=ScoreEvidenceCandidates(),
    )
    result = await service.execute(
        SearchEvidenceCandidatesRequest(
            claim="Kassenstellen",
            claim_type=ClaimType.QUANTITATIVE,
            snapshot_id="snap_1",
        )
    )

    assert {candidate.passage_id for candidate in result.candidates} == {
        "psg_compound",
        "psg_parts",
    }
