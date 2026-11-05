"""Repository ports consumed by the application layer (contract frozen, issue #205).

Protocols live beside their consumers; ``infrastructure/repository/ports.py`` re-exports them as
the implementation boundary. Database columns are deliberately out of scope.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from simulation_orchestration.application.dto import (
    InvocationEnvelope,
    JobRecord,
    ProgressEventView,
    UsageAggregate,
)
from simulation_orchestration.application.values import (
    JobId,
    PromptTemplate,
    RunId,
)


@runtime_checkable
class JobStore(Protocol):
    async def add(self, job: JobRecord) -> None: ...

    async def get(self, job_id: JobId) -> JobRecord | None: ...

    async def get_by_run(self, run_id: RunId) -> JobRecord | None: ...

    async def save(self, job: JobRecord) -> None: ...

    async def claim_next(self, worker_id: str, now: datetime) -> JobRecord | None: ...

    async def list_resumable(self) -> Sequence[JobRecord]: ...


@runtime_checkable
class InvocationStore(Protocol):
    async def add(self, envelope: InvocationEnvelope) -> None: ...

    async def list_for_run(self, run_id: RunId) -> Sequence[InvocationEnvelope]: ...

    async def usage_for_run(self, run_id: RunId) -> UsageAggregate: ...


@runtime_checkable
class ProgressStore(Protocol):
    async def append(self, event: ProgressEventView) -> ProgressEventView: ...

    async def list_after(
        self, run_id: RunId, after_sequence: int, limit: int
    ) -> Sequence[ProgressEventView]: ...

    async def latest_sequence(self, run_id: RunId) -> int: ...


@runtime_checkable
class PromptRegistry(Protocol):
    async def register(self, name: str, body: str) -> PromptTemplate: ...

    async def get(self, name: str, version: int) -> PromptTemplate | None: ...

    async def latest(self, name: str) -> PromptTemplate | None: ...

    async def list_versions(self, name: str) -> Sequence[PromptTemplate]: ...
