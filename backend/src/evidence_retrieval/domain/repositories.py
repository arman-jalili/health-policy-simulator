"""Domain-owned repository and open-host ports of EvidenceRetrieval (ADR-001, ADR-003).

Canonical: .pi/architecture/modules/evidence-retrieval.md

``PassageSearchPort`` is the published language consumed from EvidenceCorpus. No code in this
context may read ``evidence_corpus_*`` tables directly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from evidence_corpus.domain.published import PassageView, SnapshotIndexView
from evidence_corpus.domain.values import AuthorityRule, ClaimType
from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.values import ClaimText, PackId, SnapshotId


@runtime_checkable
class EvidencePackRepository(Protocol):
    """Persistence port for the EvidencePack aggregate (one aggregate per transaction)."""

    async def get(self, pack_id: PackId) -> EvidencePack | None: ...

    async def save(self, pack: EvidencePack) -> None: ...

    async def latest_for_claim(self, claim: ClaimText) -> EvidencePack | None: ...


@runtime_checkable
class PassageSearchPort(Protocol):
    """Published language consumed from EvidenceCorpus — no corpus tables touched."""

    async def search(
        self, query: str, snapshot_id: SnapshotId, limit: int
    ) -> list[PassageView]: ...

    async def authority_rule(self, claim_type: ClaimType) -> AuthorityRule: ...

    async def snapshot_index(self, snapshot_id: SnapshotId) -> SnapshotIndexView: ...

    async def dense_search(
        self, query: str, snapshot_id: SnapshotId, limit: int
    ) -> list[tuple[PassageView, float]]: ...
