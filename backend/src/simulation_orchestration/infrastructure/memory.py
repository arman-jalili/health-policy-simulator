"""In-memory adapters used by component tests and local wiring (issues #208+)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from simulation_orchestration.application.dto import (
    InvocationEnvelope,
    JobRecord,
    ProgressEventView,
    RoundUsage,
    StakeholderUsage,
    UsageAggregate,
)
from simulation_orchestration.application.rules import PromptVersioning
from simulation_orchestration.application.values import JobId, JobStatus, PromptTemplate, RunId


class InMemoryInvocationStore:
    """Append-only envelope store, unique on invocation id, with real usage aggregation."""

    def __init__(self) -> None:
        self._envelopes: dict[str, InvocationEnvelope] = {}

    async def add(self, envelope: InvocationEnvelope) -> None:
        self._envelopes.setdefault(str(envelope.invocation_id), envelope)

    async def list_for_run(self, run_id: RunId) -> list[InvocationEnvelope]:
        return [item for item in self._envelopes.values() if item.run_id == run_id]

    async def usage_for_run(self, run_id: RunId) -> UsageAggregate:
        envelopes = await self.list_for_run(run_id)
        by_stakeholder: dict[str, list[InvocationEnvelope]] = {}
        by_round: dict[int, list[InvocationEnvelope]] = {}
        for envelope in envelopes:
            by_stakeholder.setdefault(envelope.stakeholder, []).append(envelope)
            by_round.setdefault(envelope.round, []).append(envelope)
        return UsageAggregate(
            invocations=len(envelopes),
            input_tokens=sum(item.input_tokens for item in envelopes),
            output_tokens=sum(item.output_tokens for item in envelopes),
            cost=sum((item.cost_estimate for item in envelopes), Decimal("0")),
            by_stakeholder=tuple(
                _stakeholder_usage(name, items) for name, items in sorted(by_stakeholder.items())
            ),
            by_round=tuple(
                _round_usage(round_no, items) for round_no, items in sorted(by_round.items())
            ),
        )


def _stakeholder_usage(name: str, items: list[InvocationEnvelope]) -> StakeholderUsage:
    return StakeholderUsage(
        stakeholder=name,
        invocations=len(items),
        input_tokens=sum(item.input_tokens for item in items),
        output_tokens=sum(item.output_tokens for item in items),
        cost=sum((item.cost_estimate for item in items), Decimal("0")),
    )


def _round_usage(round_no: int, items: list[InvocationEnvelope]) -> RoundUsage:
    return RoundUsage(
        round=round_no,
        invocations=len(items),
        input_tokens=sum(item.input_tokens for item in items),
        output_tokens=sum(item.output_tokens for item in items),
        cost=sum((item.cost_estimate for item in items), Decimal("0")),
    )


class InMemoryJobStore:
    """Job store with optimistic save; one claim per queued job."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    async def add(self, job: JobRecord) -> None:
        self._jobs.setdefault(str(job.job_id), job)

    async def get(self, job_id: JobId) -> JobRecord | None:
        return self._jobs.get(str(job_id))

    async def get_by_run(self, run_id: RunId) -> JobRecord | None:
        for job in self._jobs.values():
            if job.run_id == run_id:
                return job
        return None

    async def save(self, job: JobRecord) -> None:
        self._jobs[str(job.job_id)] = job

    async def claim_next(self, worker_id: str, now: datetime) -> JobRecord | None:
        for job in self._jobs.values():
            if job.status is JobStatus.QUEUED:
                claimed = replace(
                    job,
                    status=JobStatus.RUNNING,
                    attempts=job.attempts + 1,
                    claimed_by=worker_id,
                    updated_at=now,
                )
                self._jobs[str(job.job_id)] = claimed
                return claimed
        return None

    async def list_resumable(self) -> list[JobRecord]:
        return [
            job
            for job in self._jobs.values()
            if job.status in {JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.PAUSED}
        ]


class InMemoryProgressStore:
    """Append-only progress log ordered by per-run sequence."""

    def __init__(self) -> None:
        self._events: dict[str, list[ProgressEventView]] = {}

    async def append(self, event: ProgressEventView) -> ProgressEventView:
        stream = self._events.setdefault(str(event.run_id), [])
        if any(item.sequence == event.sequence for item in stream):
            raise ValueError(f"duplicate progress sequence {event.sequence}")
        stream.append(event)
        stream.sort(key=lambda item: item.sequence)
        return event

    async def list_after(
        self, run_id: RunId, after_sequence: int, limit: int
    ) -> list[ProgressEventView]:
        return [
            item for item in self._events.get(str(run_id), []) if item.sequence > after_sequence
        ][:limit]

    async def latest_sequence(self, run_id: RunId) -> int:
        stream = self._events.get(str(run_id), [])
        return stream[-1].sequence if stream else 0

    async def max_sequence(self, run_id: RunId) -> int:
        return await self.latest_sequence(run_id)

    async def get(self, event_id: str) -> ProgressEventView | None:
        for stream in self._events.values():
            for event in stream:
                if event.event_id == event_id:
                    return event
        return None


class InMemoryPromptRegistry:
    """Append-only prompt versions; name+version is unique."""

    def __init__(self, versioning: PromptVersioning | None = None) -> None:
        self._versioning = versioning or PromptVersioning()
        self._templates: dict[tuple[str, int], PromptTemplate] = {}

    async def register(self, name: str, body: str) -> PromptTemplate:
        existing = await self.list_versions(name)
        template = self._versioning.next_version(existing=existing, name=name, body=body)
        await self.save(template)
        return template

    async def save(self, template: PromptTemplate) -> None:
        self._templates[(template.name, template.version)] = template

    async def get(self, name: str, version: int) -> PromptTemplate | None:
        return self._templates.get((name, version))

    async def latest(self, name: str) -> PromptTemplate | None:
        versions = await self.list_versions(name)
        return max(versions, key=lambda item: item.version) if versions else None

    async def list_versions(self, name: str) -> list[PromptTemplate]:
        return sorted(
            (item for (item_name, _), item in self._templates.items() if item_name == name),
            key=lambda item: item.version,
        )
