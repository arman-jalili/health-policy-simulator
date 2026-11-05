"""Hybrid search: a German compound query finds hits a naive term query misses."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date

import pytest

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
from evidence_retrieval.application.commands import SearchEvidenceCandidatesRequest
from evidence_retrieval.application.services import SearchEvidenceCandidates
from evidence_retrieval.domain.services import (
    ReciprocalRankFusion,
    ScoreEvidenceCandidates,
    StanceClassifier,
)
from evidence_retrieval.domain.values import SnapshotId, StanceLabel
from evidence_retrieval.infrastructure.adapters import (
    HashingEmbedding,
    OverlapReranker,
    RuleBasedStanceModel,
)
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

    async def snapshot_index(self, snapshot_id: SnapshotId) -> SnapshotIndexView:
        return SnapshotIndexView(index_version="idx-test", embedding_model="none")

    async def dense_search(
        self, query: str, snapshot_id: SnapshotId, limit: int
    ) -> list[tuple[PassageView, float]]:
        return []


class FakeStanceClassifier:
    async def classify(self, claim: str, passage: PassageView) -> StanceLabel:
        return StanceLabel.SUPPORTING


class DenseFakePassageSearch:
    def __init__(self, passages: list[PassageView]) -> None:
        self.passages = passages

    async def search(self, query: str, snapshot_id: SnapshotId, limit: int) -> list[PassageView]:
        return self.passages[:limit]

    async def dense_search(
        self, query: str, snapshot_id: SnapshotId, limit: int
    ) -> list[tuple[PassageView, float]]:
        return [(passage, 0.8) for passage in self.passages[:limit]]

    async def authority_rule(self, claim_type: ClaimType) -> AuthorityRule:
        return authority_rule(claim_type)

    async def snapshot_index(self, snapshot_id: SnapshotId) -> SnapshotIndexView:
        return SnapshotIndexView(
            index_version="idx-dense",
            embedding_model=HashingEmbedding.model_id,
        )


class LexicalOnlyFakePassageSearch(DenseFakePassageSearch):
    async def snapshot_index(self, snapshot_id: SnapshotId) -> SnapshotIndexView:
        return SnapshotIndexView(index_version="idx-lexical", embedding_model="none")


class TrackingFusion(ReciprocalRankFusion):
    def __init__(self) -> None:
        self.calls = 0

    def fuse(self, rankings: Sequence[Sequence[PassageView]], *, k: int = 60) -> list[PassageView]:
        self.calls += 1
        return super().fuse(rankings, k=k)


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
    assert result.query_rewrite.startswith("Kassenstellen OR ")


async def test_hybrid_path_calls_fusion_and_records_the_mode() -> None:
    passage = _passage("psg_compound", "Die Kassenstellen werden aufgestockt.")
    fusion = TrackingFusion()
    service = SearchEvidenceCandidates(
        search_port=DenseFakePassageSearch([passage]),
        query_rewrite=GermanQueryRewrite(),
        fusion=fusion,
        stance_classifier=StanceClassifier(RuleBasedStanceModel()),
        scorer=ScoreEvidenceCandidates(),
    )

    result = await service.execute(
        SearchEvidenceCandidatesRequest(
            claim="Kassenstellen",
            claim_type=ClaimType.QUANTITATIVE,
            snapshot_id="snap_1",
        )
    )

    assert fusion.calls == 1
    assert result.retrieval_mode == "lexical+dense"
    assert result.embedding_model == HashingEmbedding.model_id
    assert result.candidates[0].score.semantic == 0.8


async def test_reranker_changes_order_for_a_known_claim() -> None:
    generic = _passage("psg_generic", "Die Kasse wird aufgestockt.")
    exact = _passage("psg_exact", "Die Kassenvertragsstellen werden aufgestockt.")
    reranked = await OverlapReranker().rerank("Kassenvertragsstellen", [generic, exact], limit=2)

    assert [passage.passage_id for passage in reranked] == ["psg_exact", "psg_generic"]


async def test_hashing_embedding_is_deterministic_and_compound_sensitive() -> None:
    embedding = HashingEmbedding()
    first, second, unrelated = await embedding.embed(
        ["Kassenvertragsstellen", "Kassenvertragsstellen", "Wetterbericht"]
    )

    assert first == second
    assert math.isclose(sum(value * value for value in first), 1.0, abs_tol=1e-12)
    assert sum(a * b for a, b in zip(first, unrelated, strict=True)) < 0.1


async def test_unbound_dense_port_keeps_semantic_zero_and_mode_lexical() -> None:
    passage = _passage("psg_lexical", "Die Kassenstellen werden aufgestockt.")
    fusion = TrackingFusion()
    service = SearchEvidenceCandidates(
        search_port=LexicalOnlyFakePassageSearch([passage]),
        query_rewrite=GermanQueryRewrite(),
        fusion=fusion,
        stance_classifier=StanceClassifier(RuleBasedStanceModel()),
        scorer=ScoreEvidenceCandidates(),
    )

    result = await service.execute(
        SearchEvidenceCandidatesRequest(
            claim="Kassenstellen",
            claim_type=ClaimType.QUANTITATIVE,
            snapshot_id="snap_1",
        )
    )

    assert fusion.calls == 0
    assert result.retrieval_mode == "lexical"
    assert result.embedding_model == "none"
    assert result.candidates[0].score.semantic == 0.0
