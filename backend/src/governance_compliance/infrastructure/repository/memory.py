"""In-memory append-only stores for tests and local runs."""

from __future__ import annotations

from collections.abc import Sequence

from governance_compliance.application.dto import ProvenanceRecord, ViolationRecord
from governance_compliance.application.values import PositionId, RunId, ViolationClass


class InMemoryViolationStore:
    def __init__(self) -> None:
        self._rows: dict[str, ViolationRecord] = {}

    async def add(self, record: ViolationRecord) -> ViolationRecord:
        self._rows.setdefault(record.violation_hash, record)
        return self._rows[record.violation_hash]

    async def get_by_hash(self, violation_hash: str) -> ViolationRecord | None:
        return self._rows.get(violation_hash)

    async def list(
        self,
        *,
        run_id: RunId | None = None,
        violation_class: ViolationClass | None = None,
        limit: int = 100,
    ) -> Sequence[ViolationRecord]:
        rows = [
            row
            for row in self._rows.values()
            if (run_id is None or row.run_id == run_id)
            and (violation_class is None or row.violation_class is violation_class)
        ]
        return tuple(sorted(rows, key=lambda row: row.detected_at, reverse=True)[:limit])


class InMemoryProvenanceStore:
    def __init__(self) -> None:
        self._rows: dict[tuple[str, int], ProvenanceRecord] = {}

    async def save(self, record: ProvenanceRecord) -> ProvenanceRecord:
        self._rows[(str(record.position_id), record.version)] = record
        return record

    async def get(
        self, position_id: PositionId, version: int | None = None
    ) -> ProvenanceRecord | None:
        rows = [row for (pid, _), row in self._rows.items() if pid == str(position_id)]
        if not rows:
            return None
        if version is not None:
            return next((row for row in rows if row.version == version), None)
        return max(rows, key=lambda row: row.version)

    async def list_for_position(self, position_id: PositionId) -> Sequence[ProvenanceRecord]:
        rows = [row for (pid, _), row in self._rows.items() if pid == str(position_id)]
        return tuple(sorted(rows, key=lambda row: row.version))
