"""Durable append-only stores for GovernanceCompliance."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from governance_compliance.application.dto import ProvenanceRecord, ViolationRecord
from governance_compliance.application.values import (
    GuardRuleId,
    InvocationId,
    PositionId,
    RunId,
    ViolationClass,
    ViolationId,
)
from governance_compliance.infrastructure.repository.models import ProvenanceRow, ViolationRow


def _violation(row: ViolationRow) -> ViolationRecord:
    return ViolationRecord(
        violation_id=ViolationId(row.id),
        run_id=RunId(row.run_id),
        invocation_id=InvocationId(row.invocation_id),
        violation_class=ViolationClass(row.violation_class),
        offending_span=row.offending_span,
        rewritten_span=row.rewritten_span,
        rule_id=GuardRuleId(row.rule_id),
        rule_version=row.rule_version,
        violation_hash=row.violation_hash,
        detected_at=row.detected_at,
    )


def _provenance(row: ProvenanceRow) -> ProvenanceRecord:
    return ProvenanceRecord(
        position_id=PositionId(row.position_id),
        evidence_ids=tuple(row.evidence_ids),
        argument_ids=tuple(row.argument_ids),
        invocation_id=row.invocation_id,
        prompt_version=row.prompt_version,
        model=row.model,
        disclosed_at=row.disclosed_at,
        version=row.version,
    )


class SqlAlchemyViolationStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(self, record: ViolationRecord) -> ViolationRecord:
        async with self._session_factory() as session, session.begin():
            existing = await session.scalar(
                select(ViolationRow).where(ViolationRow.violation_hash == record.violation_hash)
            )
            if existing is not None:
                return _violation(existing)
            session.add(
                ViolationRow(
                    id=str(record.violation_id),
                    run_id=str(record.run_id),
                    invocation_id=str(record.invocation_id),
                    violation_class=record.violation_class.value,
                    offending_span=record.offending_span,
                    rewritten_span=record.rewritten_span,
                    rule_id=record.rule_id.value,
                    rule_version=record.rule_version,
                    violation_hash=record.violation_hash,
                    detected_at=record.detected_at,
                )
            )
        return record

    async def get_by_hash(self, violation_hash: str) -> ViolationRecord | None:
        async with self._session_factory() as session:
            row = await session.scalar(
                select(ViolationRow).where(ViolationRow.violation_hash == violation_hash)
            )
            return _violation(row) if row is not None else None

    async def list(
        self,
        *,
        run_id: RunId | None = None,
        violation_class: ViolationClass | None = None,
        limit: int = 100,
    ) -> Sequence[ViolationRecord]:
        query = select(ViolationRow).order_by(ViolationRow.detected_at.desc()).limit(limit)
        if run_id is not None:
            query = query.where(ViolationRow.run_id == str(run_id))
        if violation_class is not None:
            query = query.where(ViolationRow.violation_class == violation_class.value)
        async with self._session_factory() as session:
            rows = (await session.scalars(query)).all()
            return tuple(_violation(row) for row in rows)


class SqlAlchemyProvenanceStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, record: ProvenanceRecord) -> ProvenanceRecord:
        async with self._session_factory() as session, session.begin():
            existing = await session.get(
                ProvenanceRow, {"position_id": str(record.position_id), "version": record.version}
            )
            if existing is not None:
                return _provenance(existing)
            session.add(
                ProvenanceRow(
                    position_id=str(record.position_id),
                    version=record.version,
                    evidence_ids=list(record.evidence_ids),
                    argument_ids=list(record.argument_ids),
                    invocation_id=record.invocation_id,
                    prompt_version=record.prompt_version,
                    model=record.model,
                    disclosed_at=record.disclosed_at,
                )
            )
        return record

    async def get(
        self, position_id: PositionId, version: int | None = None
    ) -> ProvenanceRecord | None:
        query = select(ProvenanceRow).where(ProvenanceRow.position_id == str(position_id))
        query = query.order_by(ProvenanceRow.version.desc())
        if version is not None:
            query = query.where(ProvenanceRow.version == version)
        async with self._session_factory() as session:
            row = await session.scalar(query.limit(1))
            return _provenance(row) if row is not None else None

    async def list_for_position(self, position_id: PositionId) -> Sequence[ProvenanceRecord]:
        query = (
            select(ProvenanceRow)
            .where(ProvenanceRow.position_id == str(position_id))
            .order_by(ProvenanceRow.version)
        )
        async with self._session_factory() as session:
            rows = (await session.scalars(query)).all()
            return tuple(_provenance(row) for row in rows)
