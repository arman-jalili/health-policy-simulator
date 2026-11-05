"""Measure lexical vs hybrid recall on a deterministic 50-claim labelled set.

Canonical: .pi/architecture/modules/evidence-retrieval.md (Evaluation)

The script is a CI/analyst tool, not an application service. It seeds an in-memory corpus, runs the
same labelled cases through a lexical-only service and the wired hybrid service, and writes JSON to
stdout. CI uploads the JSON as an artifact; no recall threshold is compiled into code.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime

from evidence_corpus.domain.entities import CorpusSnapshot, IndexManifest
from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import ClaimType, Offsets, SourceType, SpeakerKind
from evidence_retrieval.application.services import SearchEvidenceCandidates
from evidence_retrieval.domain.services import (
    ApplyRecencyPolicy,
    ReciprocalRankFusion,
    ScoreEvidenceCandidates,
    StanceClassifier,
)
from evidence_retrieval.domain.values import SnapshotId
from evidence_retrieval.evaluation import EvaluationCase, EvaluationHarness
from evidence_retrieval.infrastructure.adapters import (
    CorpusPassageSearch,
    OverlapReranker,
    RuleBasedStanceModel,
    SystemClock,
)
from evidence_retrieval.infrastructure.query_rewrite import GermanQueryRewrite
from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence

CASE_COUNT = 50


def _passage(index: int) -> PassageView:
    claim = f"Kassenstellen{index}"
    text = f"Die {claim} werden aufgestockt."
    return PassageView(
        passage_id=f"psg_{index}",
        article_id="art_eval",
        document_id="doc_eval",
        text=text,
        provenance=ProvenanceView(
            outlet="Evaluationskorpus",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, len(text)),
            source_uri="s3://corpus/eval.pdf",
        ),
        speaker_kind=SpeakerKind.INSTITUTION,
        citable=True,
        source_type=SourceType.INSTITUTIONAL_STATEMENT,
    )


async def _run() -> dict[str, object]:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://hps:hps@localhost:5433/health_policy",
        persistence=Persistence.MEMORY,
        auth_mode=AuthMode.DEMO,
    )
    app = create_app(settings)
    corpus = app.state.corpus
    container = app.state.evidence_retrieval
    passages = [_passage(index) for index in range(CASE_COUNT)]
    manifest = await corpus.index_writer.upsert_passages("doc_eval", passages)
    snapshot = CorpusSnapshot.pin(
        label="evaluation",
        document_ids=["doc_eval"],
        index_manifest=IndexManifest(
            index_version=manifest.index_version,
            embedding_model=manifest.embedding_model,
            searchable_since=manifest.searchable_since,
            passage_count=manifest.passage_count,
        ),
        pinned_at=datetime.now(tz=UTC),
        manifest_hash="sha256:evaluation",
    )
    await corpus.snapshots.save(snapshot)

    lexical_search = SearchEvidenceCandidates(
        search_port=CorpusPassageSearch(
            index=corpus.index_writer,
            passages=corpus.passages,
            snapshots=corpus.snapshots,
            authority_rules=corpus.authority_rules,
            embeddings=None,
        ),
        query_rewrite=GermanQueryRewrite(),
        fusion=ReciprocalRankFusion(),
        stance_classifier=StanceClassifier(RuleBasedStanceModel()),
        scorer=ScoreEvidenceCandidates(),
        recency=ApplyRecencyPolicy(),
        clock=SystemClock(),
        reranker=OverlapReranker(),
    )
    cases = [
        EvaluationCase(
            claim=f"Kassenstellen{index}",
            claim_type=ClaimType.QUALITATIVE,
            snapshot_id=SnapshotId(snapshot.id),
            relevant_passage_ids=frozenset({f"psg_{index}"}),
        )
        for index in range(CASE_COUNT)
    ]
    lexical = await EvaluationHarness(lexical_search, retrieval_mode="lexical").run(cases)
    hybrid = await EvaluationHarness(
        container.search_candidates, retrieval_mode="lexical+dense"
    ).run(cases)
    return {
        "case_count": lexical.case_count,
        "lexical": {
            "recall_at_k": lexical.recall_at_k,
            "per_case_recall": dict(lexical.per_case_recall),
            "retrieval_mode": lexical.retrieval_mode,
        },
        "hybrid": {
            "recall_at_k": hybrid.recall_at_k,
            "per_case_recall": dict(hybrid.per_case_recall),
            "retrieval_mode": hybrid.retrieval_mode,
        },
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(_run()), indent=2, sort_keys=True))
