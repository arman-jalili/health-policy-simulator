"""PostgreSQL adapters for SimulationOrchestration (issue #217)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from simulation_orchestration.application.dto import (
    InvocationEnvelope,
    JobRecord,
    ProgressEventView,
    RoundUsage,
    StakeholderUsage,
    UsageAggregate,
)
from simulation_orchestration.application.rules import PromptVersioning
from simulation_orchestration.application.values import (
    BudgetUsage,
    GraphState,
    InvocationId,
    InvocationOutcome,
    JobId,
    JobStatus,
    ProgressKind,
    PromptId,
    PromptRef,
    PromptTemplate,
    RunBudget,
    RunId,
    RunPhase,
)
from simulation_orchestration.infrastructure.repository.models import (
    InvocationRow,
    JobRow,
    ProgressRow,
    PromptRow,
)


def _state_payload(state: GraphState) -> dict[str, Any]:
    return {
        "run_id": str(state.run_id),
        "round": state.round,
        "phase": state.phase.value,
        "next_actor": state.next_actor,
        "budget_used": {
            "invocations": state.budget_used.invocations,
            "tokens": state.budget_used.tokens,
            "cost": str(state.budget_used.cost),
        },
    }


def _state_from(payload: dict[str, Any]) -> GraphState:
    usage = payload.get("budget_used", {})
    return GraphState(
        run_id=RunId(payload["run_id"]),
        round=int(payload["round"]),
        phase=RunPhase(payload["phase"]),
        next_actor=payload.get("next_actor"),
        budget_used=BudgetUsage(
            invocations=int(usage.get("invocations", 0)),
            tokens=int(usage.get("tokens", 0)),
            cost=Decimal(str(usage.get("cost", "0"))),
        ),
    )


def _budget_payload(budget: RunBudget) -> dict[str, Any]:
    return {
        "max_invocations": budget.max_invocations,
        "max_tokens": budget.max_tokens,
        "max_cost": str(budget.max_cost) if budget.max_cost is not None else None,
    }


def _budget_from(payload: dict[str, Any]) -> RunBudget:
    cost = payload.get("max_cost")
    return RunBudget(
        max_invocations=payload.get("max_invocations"),
        max_tokens=payload.get("max_tokens"),
        max_cost=Decimal(str(cost)) if cost is not None else None,
    )


def _job_from(row: JobRow) -> JobRecord:
    return JobRecord(
        job_id=JobId(row.id),
        run_id=RunId(row.run_id),
        status=JobStatus(row.status),
        attempts=row.attempts,
        checkpoint=_state_from(row.checkpoint),
        budget_used=_state_from(row.checkpoint).budget_used,
        error=row.error,
        claimed_by=row.claimed_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
        budget=_budget_from(row.budget),
    )


def _job_row(job: JobRecord) -> JobRow:
    return JobRow(
        id=str(job.job_id),
        run_id=str(job.run_id),
        status=job.status.value,
        attempts=job.attempts,
        checkpoint=_state_payload(job.checkpoint),
        budget_used=_state_payload(job.checkpoint)["budget_used"],
        budget=_budget_payload(job.budget),
        error=job.error,
        claimed_by=job.claimed_by,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


class SqlAlchemyJobStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(self, job: JobRecord) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(_job_row(job))

    async def get(self, job_id: JobId) -> JobRecord | None:
        async with self._session_factory() as session:
            row = await session.get(JobRow, str(job_id))
        return _job_from(row) if row is not None else None

    async def get_by_run(self, run_id: RunId) -> JobRecord | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(JobRow)
                .where(JobRow.run_id == str(run_id))
                .order_by(JobRow.created_at.desc())
                .limit(1)
            )
        return _job_from(row) if row is not None else None

    async def save(self, job: JobRecord) -> None:
        async with self._session_factory() as session, session.begin():
            await session.merge(_job_row(job))

    async def claim_next(self, worker_id: str, now: datetime) -> JobRecord | None:
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(
                select(JobRow)
                .where(JobRow.status == JobStatus.QUEUED.value)
                .order_by(JobRow.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if row is None:
                return None
            row.status = JobStatus.RUNNING.value
            row.attempts += 1
            row.claimed_by = worker_id
            row.updated_at = now
            await session.flush()
            return _job_from(row)

    async def list_resumable(self) -> list[JobRecord]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(JobRow)
                .where(
                    JobRow.status.in_(
                        [
                            JobStatus.QUEUED.value,
                            JobStatus.RUNNING.value,
                            JobStatus.PAUSED.value,
                        ]
                    )
                )
                .order_by(JobRow.created_at)
            )
        return [_job_from(row) for row in rows]


class SqlAlchemyInvocationStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(self, envelope: InvocationEnvelope) -> None:
        async with self._session_factory() as session, session.begin():
            statement = insert(InvocationRow).values(
                id=str(envelope.invocation_id),
                run_id=str(envelope.run_id),
                round=envelope.round,
                stakeholder=envelope.stakeholder,
                purpose=envelope.purpose,
                model=envelope.model,
                prompt_name=envelope.prompt.name,
                prompt_version=envelope.prompt.version,
                parameters=dict(envelope.parameters),
                evidence_pack_ids=list(envelope.evidence_pack_ids),
                input_tokens=envelope.input_tokens,
                output_tokens=envelope.output_tokens,
                cost_estimate=envelope.cost_estimate,
                latency_ms=envelope.latency_ms,
                outcome=envelope.outcome.value,
                created_at=envelope.created_at,
            )
            await session.execute(statement.on_conflict_do_nothing(index_elements=["id"]))

    async def list_for_run(self, run_id: RunId) -> list[InvocationEnvelope]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(InvocationRow)
                .where(InvocationRow.run_id == str(run_id))
                .order_by(InvocationRow.created_at, InvocationRow.id)
            )
        return [_invocation_from(row) for row in rows]

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


class SqlAlchemyProgressStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def append(self, event: ProgressEventView) -> ProgressEventView:
        async with self._session_factory() as session, session.begin():
            session.add(
                ProgressRow(
                    id=event.event_id,
                    run_id=str(event.run_id),
                    sequence=event.sequence,
                    kind=event.kind.value,
                    payload=dict(event.payload),
                    created_at=event.created_at,
                )
            )
        return event

    async def list_after(
        self, run_id: RunId, after_sequence: int, limit: int
    ) -> list[ProgressEventView]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(ProgressRow)
                .where(
                    ProgressRow.run_id == str(run_id),
                    ProgressRow.sequence > after_sequence,
                )
                .order_by(ProgressRow.sequence)
                .limit(limit)
            )
        return [_progress_from(row) for row in rows]

    async def latest_sequence(self, run_id: RunId) -> int:
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.max(ProgressRow.sequence)).where(ProgressRow.run_id == str(run_id))
            )
        return int(value or 0)

    async def get(self, event_id: str) -> ProgressEventView | None:
        async with self._session_factory() as session:
            row = await session.get(ProgressRow, event_id)
        return _progress_from(row) if row is not None else None


class SqlAlchemyPromptRegistry:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        versioning: PromptVersioning | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._versioning = versioning or PromptVersioning()

    async def register(self, name: str, body: str) -> PromptTemplate:
        existing = await self.list_versions(name)
        template = self._versioning.next_version(existing=existing, name=name, body=body)
        await self.save(template)
        return template

    async def save(self, template: PromptTemplate) -> None:
        async with self._session_factory() as session, session.begin():
            await session.merge(
                PromptRow(
                    id=str(template.id),
                    name=template.name,
                    version=template.version,
                    body=template.body,
                    checksum=template.checksum,
                    created_at=template.created_at,
                )
            )

    async def get(self, name: str, version: int) -> PromptTemplate | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(PromptRow).where(PromptRow.name == name, PromptRow.version == version)
            )
        return _prompt_from(row) if row is not None else None

    async def latest(self, name: str) -> PromptTemplate | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(PromptRow)
                .where(PromptRow.name == name)
                .order_by(PromptRow.version.desc())
                .limit(1)
            )
        return _prompt_from(row) if row is not None else None

    async def list_versions(self, name: str) -> list[PromptTemplate]:
        async with self._session_factory() as session:
            rows = await session.scalars(
                select(PromptRow).where(PromptRow.name == name).order_by(PromptRow.version)
            )
        return [_prompt_from(row) for row in rows]


def _invocation_from(row: InvocationRow) -> InvocationEnvelope:
    return InvocationEnvelope(
        invocation_id=InvocationId(row.id),
        run_id=RunId(row.run_id),
        round=row.round,
        stakeholder=row.stakeholder,
        purpose=row.purpose,
        model=row.model,
        prompt=PromptRef(row.prompt_name, row.prompt_version),
        parameters=dict(row.parameters),
        evidence_pack_ids=tuple(row.evidence_pack_ids),
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        cost_estimate=Decimal(str(row.cost_estimate)),
        latency_ms=row.latency_ms,
        outcome=InvocationOutcome(row.outcome),
        created_at=row.created_at,
    )


def _progress_from(row: ProgressRow) -> ProgressEventView:
    return ProgressEventView(
        event_id=row.id,
        run_id=RunId(row.run_id),
        sequence=row.sequence,
        kind=ProgressKind(row.kind),
        payload=dict(row.payload),
        created_at=row.created_at,
    )


def _prompt_from(row: PromptRow) -> PromptTemplate:
    return PromptTemplate(
        id=PromptId(row.id),
        name=row.name,
        version=row.version,
        body=row.body,
        checksum=row.checksum,
        created_at=row.created_at,
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
