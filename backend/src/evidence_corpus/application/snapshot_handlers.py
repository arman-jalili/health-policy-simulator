"""Corpus snapshot use cases: pin the manifest a run may search, and read it back.

Canonical: .pi/architecture/modules/evidence-corpus.md

A snapshot is a manifest, not a corpus-wide transaction: it records the document ids and the index
version, hashed together, so a citation resolved through it stays valid after later ingestion.
"""

from __future__ import annotations

import hashlib

from evidence_corpus.application.commands import (
    GetCorpusSnapshotRequest,
    PinCorpusSnapshotRequest,
)
from evidence_corpus.application.dto import IndexManifestView, SnapshotView
from evidence_corpus.application.events import EventPublisher
from evidence_corpus.domain.entities import CorpusSnapshot, IndexManifest
from evidence_corpus.domain.errors import DocumentNotFound, SnapshotNotFound
from evidence_corpus.domain.events import IndexManifestPublished
from evidence_corpus.domain.repositories import CorpusSnapshotRepository, DocumentRepository
from shared.clock import Clock, SystemClock

_DOCUMENT_SCAN_LIMIT = 10_000


class PinCorpusSnapshotHandler:
    """Implements :class:`evidence_corpus.application.services.PinCorpusSnapshot`."""

    def __init__(
        self,
        documents: DocumentRepository,
        snapshots: CorpusSnapshotRepository,
        events: EventPublisher,
        clock: Clock | None = None,
        actor: str = "system",
    ) -> None:
        self._documents = documents
        self._snapshots = snapshots
        self._events = events
        self._clock = clock or SystemClock()
        self._actor = actor

    async def execute(self, request: PinCorpusSnapshotRequest) -> SnapshotView:
        document_ids = await self._resolve_document_ids(request)
        manifest = await self._snapshots.current_index_manifest()

        snapshot = CorpusSnapshot.pin(
            label=request.label,
            document_ids=document_ids,
            index_manifest=manifest,
            pinned_at=self._clock.now(),
            manifest_hash=_manifest_hash(document_ids, manifest),
        )
        await self._snapshots.save(snapshot)
        await self._events.publish(
            [
                IndexManifestPublished(
                    snapshot_id=snapshot.id,
                    index_version=manifest.index_version,
                    embedding_model=manifest.embedding_model,
                    passage_count=manifest.passage_count,
                )
            ],
            actor=self._actor,
        )
        return snapshot_view(snapshot)

    async def _resolve_document_ids(self, request: PinCorpusSnapshotRequest) -> list[str]:
        if request.document_ids is None:
            return await self._documents.next_documents(_DOCUMENT_SCAN_LIMIT)

        found = await self._documents.list_by_ids(request.document_ids)
        missing = sorted(set(request.document_ids) - {document.id for document in found})
        if missing:
            raise DocumentNotFound(missing[0])
        return [document.id for document in found]


class GetCorpusSnapshotHandler:
    """Implements :class:`evidence_corpus.application.services.GetCorpusSnapshot`."""

    def __init__(self, snapshots: CorpusSnapshotRepository) -> None:
        self._snapshots = snapshots

    async def execute(self, request: GetCorpusSnapshotRequest) -> SnapshotView:
        snapshot = await self._snapshots.get(request.snapshot_id)
        if snapshot is None:
            raise SnapshotNotFound(request.snapshot_id)
        return snapshot_view(snapshot)


def snapshot_view(snapshot: CorpusSnapshot) -> SnapshotView:
    manifest = snapshot.index_manifest
    return SnapshotView(
        snapshot_id=snapshot.id,
        label=snapshot.label,
        manifest_hash=snapshot.manifest_hash,
        pinned_at=snapshot.pinned_at,
        document_ids=list(snapshot.document_ids),
        index=IndexManifestView(
            index_version=manifest.index_version,
            embedding_model=manifest.embedding_model,
            searchable_since=manifest.searchable_since,
            passage_count=manifest.passage_count,
        ),
    )


def _manifest_hash(document_ids: list[str], manifest: IndexManifest) -> str:
    payload = "|".join([manifest.index_version, *sorted(document_ids)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
