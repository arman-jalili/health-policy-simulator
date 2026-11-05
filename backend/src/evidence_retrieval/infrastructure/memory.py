"""In-memory EvidencePack repository for tests and the explicit local demo.

Canonical: .pi/architecture/modules/evidence-retrieval.md

The memory adapter is never selected implicitly (ADR-002); composition only uses it for tests and
``PERSISTENCE=memory`` in local mode.
"""

from __future__ import annotations

from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.values import ClaimText, PackId


class InMemoryEvidencePackRepository:
    """Process-local repository; restart loses packs, which is acceptable only for demos/tests."""

    def __init__(self) -> None:
        self._packs: dict[str, EvidencePack] = {}

    async def get(self, pack_id: PackId) -> EvidencePack | None:
        return self._packs.get(str(pack_id))

    async def save(self, pack: EvidencePack) -> None:
        self._packs[str(pack.id)] = pack

    async def latest_for_claim(self, claim: ClaimText) -> EvidencePack | None:
        matches = [pack for pack in self._packs.values() if pack.claim == claim]
        return matches[-1] if matches else None
