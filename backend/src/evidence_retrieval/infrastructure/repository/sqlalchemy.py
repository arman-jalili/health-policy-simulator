"""SQLAlchemy adapter for frozen evidence packs (ADR-002).

Canonical: .pi/architecture/modules/evidence-retrieval.md

Packs are immutable once frozen, so save is an idempotent upsert of the whole payload. The adapter
never exposes ORM rows to the domain; it reconstructs the aggregate from JSONB.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import Offsets
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
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
from evidence_retrieval.infrastructure.repository.models import EvidencePackRow


class SqlAlchemyEvidencePackRepository:
    """Implements the domain `EvidencePackRepository` port."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, pack_id: PackId) -> EvidencePack | None:
        async with self._session_factory() as session:
            payload = await session.scalar(
                select(EvidencePackRow.payload).where(EvidencePackRow.id == str(pack_id))
            )
        return _from_payload(payload) if payload is not None else None

    async def save(self, pack: EvidencePack) -> None:
        payload = _to_payload(pack)
        async with self._session_factory() as session, session.begin():
            statement = pg_insert(EvidencePackRow).values(
                id=str(pack.id), claim=str(pack.claim), payload=payload
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[EvidencePackRow.id],
                    set_={"claim": statement.excluded.claim, "payload": statement.excluded.payload},
                )
            )

    async def latest_for_claim(self, claim: ClaimText) -> EvidencePack | None:
        async with self._session_factory() as session:
            payload = await session.scalar(
                select(EvidencePackRow.payload)
                .where(EvidencePackRow.claim == str(claim))
                .order_by(EvidencePackRow.created_at.desc())
                .limit(1)
            )
        return _from_payload(payload) if payload is not None else None


def _to_payload(pack: EvidencePack) -> dict[str, Any]:
    return {
        "id": str(pack.id),
        "claim": str(pack.claim),
        "snapshot_id": str(pack.snapshot_id),
        "index_version": pack.index_version,
        "candidates": [
            {
                "passage_id": str(candidate.passage_id),
                "stance": candidate.stance.value,
                "score": {
                    "authority": candidate.score.authority,
                    "lexical": candidate.score.lexical,
                    "semantic": candidate.score.semantic,
                    "recency": candidate.score.recency,
                    "directness": candidate.score.directness,
                    "final": candidate.score.final,
                },
                "provenance": (
                    {
                        "outlet": candidate.provenance.outlet,
                        "published_on": candidate.provenance.published_on.isoformat(),
                        "medium": candidate.provenance.medium,
                        "page_from": candidate.provenance.page_from,
                        "page_to": candidate.provenance.page_to,
                        "offsets": {
                            "start": candidate.provenance.offsets.start,
                            "end": candidate.provenance.offsets.end,
                        },
                        "source_uri": candidate.provenance.source_uri,
                    }
                    if candidate.provenance is not None
                    else None
                ),
            }
            for candidate in pack.candidates
        ],
        "absence": (
            {
                "queries": list(pack.absence.queries),
                "snapshot_id": str(pack.absence.snapshot_id),
                "reason": pack.absence.reason,
            }
            if pack.absence is not None
            else None
        ),
        "trace": {
            "embedding_model": pack.trace.embedding_model,
            "reranker_model": pack.trace.reranker_model,
            "query_rewrite": {
                "original": pack.trace.query_rewrite.original,
                "expanded": pack.trace.query_rewrite.expanded,
            },
            "stance_counts": {
                stance.value: count for stance, count in pack.trace.stance_counts.items()
            },
        },
        "frozen": pack.frozen,
        "frozen_at": pack.frozen_at.isoformat() if pack.frozen_at is not None else None,
    }


def _from_payload(payload: dict[str, Any]) -> EvidencePack:
    trace = payload["trace"]
    absence = payload["absence"]
    return EvidencePack(
        id=PackId(payload["id"]),
        claim=ClaimText(payload["claim"]),
        snapshot_id=SnapshotId(payload["snapshot_id"]),
        index_version=payload["index_version"],
        trace=RetrievalTrace(
            embedding_model=trace["embedding_model"],
            reranker_model=trace["reranker_model"],
            query_rewrite=QueryRewrite(**trace["query_rewrite"]),
            stance_counts={
                StanceLabel(stance): count for stance, count in trace["stance_counts"].items()
            },
        ),
        candidates=[
            EvidenceCandidate(
                passage_id=PassageId(candidate["passage_id"]),
                stance=StanceLabel(candidate["stance"]),
                score=EvidenceScore(**candidate["score"]),
                provenance=(
                    _provenance(candidate["provenance"])
                    if candidate["provenance"] is not None
                    else None
                ),
            )
            for candidate in payload["candidates"]
        ],
        absence=(
            AbsenceFinding(
                queries=tuple(absence["queries"]),
                snapshot_id=SnapshotId(absence["snapshot_id"]),
                reason=absence["reason"],
            )
            if absence is not None
            else None
        ),
        frozen=bool(payload["frozen"]),
        frozen_at=(
            datetime.fromisoformat(payload["frozen_at"])
            if payload["frozen_at"] is not None
            else None
        ),
    )


def _provenance(payload: dict[str, Any]) -> ProvenanceView:
    return ProvenanceView(
        outlet=payload["outlet"],
        published_on=date.fromisoformat(payload["published_on"]),
        medium=payload["medium"],
        page_from=payload["page_from"],
        page_to=payload["page_to"],
        offsets=Offsets(payload["offsets"]["start"], payload["offsets"]["end"]),
        source_uri=payload["source_uri"],
    )
