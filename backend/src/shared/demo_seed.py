"""Idempotent local-demo bootstrap: corpus, snapshot, reference figures and evidence packs.

Canonical: ``docs/demo-walkthrough.md``

The seed is deliberately outside every bounded context: it drives their published use cases from
the composition root, the same way an operator would, but without an HTTP server. It is refused
outside ``ENV=local`` and safe to re-run: documents are content-addressed, snapshots are reused by
label, reference figures by measure, and packs by claim.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from claim_validation.application.commands import (
    ListReferenceFiguresRequest,
    RegisterReferenceFigureRequest,
)
from claim_validation.domain.values import MeasureReference
from evidence_corpus.application.commands import (
    IndexIngestedPassagesRequest,
    IngestDocumentRequest,
    PinCorpusSnapshotRequest,
    PublicationInput,
    SegmentArticleRequest,
)
from evidence_corpus.domain.values import ClaimType, Offsets, SourceType, SpeakerKind
from evidence_retrieval.application.commands import AssembleEvidencePackRequest
from evidence_retrieval.domain.values import ClaimText
from shared.app import create_app
from shared.config import get_settings
from shared.enums import Environment

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "demo-corpus.pdf"
SNAPSHOT_LABEL = "demo-corpus-v1"


@dataclass(frozen=True, slots=True)
class DemoTopic:
    slug: str
    claim: str


@dataclass(frozen=True, slots=True)
class DemoFigure:
    measure: str
    unit: str
    period: str
    geography: str
    value: str


DEMO_TOPICS: tuple[DemoTopic, ...] = (
    DemoTopic("kassenstellen", "Die Kassenstellen sollen ausgebaut werden."),
    DemoTopic("spitalsreform", "Die Spitalsreform verschiebt Mittel zu den Kassenstellen."),
    DemoTopic("pflegepersonal", "Das Pflegepersonal braucht mehr Ausbildung."),
    DemoTopic("arzneimittelpreise", "Die Arzneimittelpreise sollen transparent bleiben."),
    DemoTopic("digitalisierung", "Die Digitalisierung umfasst die elektronische Gesundheitsakte."),
)

DEMO_FIGURES: tuple[DemoFigure, ...] = (
    DemoFigure("Kassenstellen", "count", "2025", "AT", "1200"),
    DemoFigure("Spitalsbudget", "EUR", "2025", "AT", "12000000000"),
    DemoFigure("Pflegepersonal", "count", "2025", "AT", "78000"),
    DemoFigure("Arzneimittelausgaben", "EUR", "2025", "AT", "5400000000"),
    DemoFigure("ELGA-Teilnahme", "percent", "2025", "AT", "85"),
)


@dataclass(frozen=True, slots=True)
class DemoSeed:
    document_id: str
    snapshot_id: str
    figure_ids: tuple[str, ...]
    pack_ids: dict[str, str]

    def as_json(self) -> str:
        return json.dumps(
            {
                "document_id": self.document_id,
                "snapshot_id": self.snapshot_id,
                "figure_ids": list(self.figure_ids),
                "pack_ids": self.pack_ids,
                "topics": [asdict(topic) for topic in DEMO_TOPICS],
            },
            indent=2,
        )


async def seed_demo(app: object) -> DemoSeed:
    """Drive the published use cases; re-running creates no duplicate artefacts."""
    state = app.state  # type: ignore[attr-defined]
    settings = state.settings
    if settings.env is not Environment.LOCAL:
        raise RuntimeError("demo-seed is refused outside ENV=local")
    if not SAMPLE.is_file():
        raise RuntimeError(f"sample corpus is missing: {SAMPLE}")

    corpus = state.corpus
    content_hash = "sha256:" + hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    document = await corpus.documents.get_by_hash(content_hash)
    if document is None:
        ingested = await corpus.ingest_document.execute(
            IngestDocumentRequest(
                source_uri=str(SAMPLE),
                publication=PublicationInput(
                    outlet="Demo Corpus", published_on=date(2026, 1, 1), medium="print"
                ),
                source_type=SourceType.OFFICIAL_STATISTICS,
            )
        )
        document = await corpus.documents.get(ingested.document_id)
    if document is None:
        raise RuntimeError("seeded document disappeared")
    document_id = document.id
    if not document.articles:
        await corpus.segment_article.execute(SegmentArticleRequest(document_id=document_id))
        document = await corpus.documents.get(document_id)
        if document is None:
            raise RuntimeError("seeded document disappeared")
    # Ingestion extracts and segments; this demo seed publishes each article body as one
    # citable passage so retrieval has something real to index and cite.
    added_passage = False
    for article in document.articles:
        if article.passages:
            continue
        article.add_passage(
            text=article.body,
            offsets=Offsets(0, len(article.body)),
            speaker_kind=SpeakerKind.INSTITUTION,
        )
        added_passage = True
    if added_passage:
        await corpus.documents.save(document)
    await corpus.index_ingested_passages.execute(
        IndexIngestedPassagesRequest(document_id=document_id)
    )

    snapshot = await corpus.snapshots.get_by_label(SNAPSHOT_LABEL)
    if snapshot is None:
        pinned = await corpus.pin_corpus_snapshot.execute(
            PinCorpusSnapshotRequest(label=SNAPSHOT_LABEL, document_ids=[document_id])
        )
        snapshot_id = pinned.snapshot_id
    else:
        snapshot_id = snapshot.id

    existing_figures = await state.claim_validation.list_reference_figures.execute(
        ListReferenceFiguresRequest()
    )
    existing_measures = {
        (
            item.measure.casefold(),
            item.unit.casefold(),
            item.period.casefold(),
            item.geography,
        ): item.figure_id
        for item in existing_figures
    }
    figure_ids: list[str] = []
    for spec in DEMO_FIGURES:
        key = (
            spec.measure.casefold(),
            spec.unit.casefold(),
            spec.period.casefold(),
            spec.geography,
        )
        if key in existing_measures:
            figure_ids.append(existing_measures[key])
            continue
        registered = await state.claim_validation.register_reference_figure.execute(
            RegisterReferenceFigureRequest(
                measure=MeasureReference(
                    measure=spec.measure,
                    unit=spec.unit,
                    period=spec.period,
                    geography=spec.geography,
                ),
                value=Decimal(spec.value),
                tier="official_statistics",
                as_of="2026-01-01",
                source_id="demo-corpus",
            )
        )
        figure_ids.append(registered.figure_id)

    pack_ids: dict[str, str] = {}
    for topic in DEMO_TOPICS:
        existing_pack = await state.evidence_retrieval.packs.latest_for_claim(
            ClaimText(topic.claim)
        )
        if existing_pack is not None:
            pack_ids[topic.slug] = str(existing_pack.id)
            continue
        assembled = await state.evidence_retrieval.assemble_pack.execute(
            AssembleEvidencePackRequest(
                claim=topic.claim,
                claim_type=ClaimType.QUALITATIVE,
                snapshot_id=snapshot_id,
            )
        )
        pack_ids[topic.slug] = assembled.pack_id

    return DemoSeed(
        document_id=document_id,
        snapshot_id=snapshot_id,
        figure_ids=tuple(figure_ids),
        pack_ids=pack_ids,
    )


async def _main() -> None:
    app = create_app(get_settings())
    try:
        seed = await seed_demo(app)
        sys.stdout.write(seed.as_json() + "\n")
    finally:
        await app.state.db.dispose()


if __name__ == "__main__":  # pragma: no cover - operator entry
    asyncio.run(_main())
