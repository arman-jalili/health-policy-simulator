"""Repository ports consumed by the application layer (contract freeze, issue #248).

Protocols live beside their consumers; ``infrastructure/repository/ports.py`` re-exports them as
the implementation boundary. Database columns are deliberately out of scope.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from governance_compliance.application.dto import ProvenanceRecord, ViolationRecord
from governance_compliance.application.values import PositionId, RunId, ViolationClass


@runtime_checkable
class ViolationStore(Protocol):
    """Append-only and idempotent on ``violation_hash``."""

    async def add(self, record: ViolationRecord) -> ViolationRecord: ...

    async def get_by_hash(self, violation_hash: str) -> ViolationRecord | None: ...

    async def list(
        self,
        *,
        run_id: RunId | None = None,
        violation_class: ViolationClass | None = None,
        limit: int = 100,
    ) -> Sequence[ViolationRecord]: ...


@runtime_checkable
class ProvenanceStore(Protocol):
    """Append-only; one row per position per version."""

    async def save(self, record: ProvenanceRecord) -> ProvenanceRecord: ...

    async def get(
        self, position_id: PositionId, version: int | None = None
    ) -> ProvenanceRecord | None: ...

    async def list_for_position(self, position_id: PositionId) -> Sequence[ProvenanceRecord]: ...
