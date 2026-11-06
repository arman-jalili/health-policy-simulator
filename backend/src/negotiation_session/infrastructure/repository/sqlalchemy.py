"""PostgreSQL adapters for NegotiationSession (issue #405)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from negotiation_session.domain.events import DomainEvent, LoggedEvent
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import RunId
from negotiation_session.infrastructure.repository.models import (
    NegotiationEventRow,
    NegotiationRunRow,
)
from negotiation_session.infrastructure.repository.serialization import (
    decode,
    decode_run,
    encode,
    encode_run,
)


class SqlAlchemySimulationRunRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, run_id: RunId) -> SimulationRun | None:
        async with self._session_factory() as session:
            row = await session.get(NegotiationRunRow, str(run_id))
            return decode_run(row.snapshot) if row is not None else None

    async def all_ids(self) -> Sequence[RunId]:
        async with self._session_factory() as session:
            rows = (await session.scalars(select(NegotiationRunRow.id))).all()
        return tuple(RunId(str(row)) for row in rows)

    async def save(self, run: SimulationRun) -> None:
        payload = encode_run(run)
        async with self._session_factory() as session:
            statement = insert(NegotiationRunRow).values(
                id=str(run.id),
                phase=run.phase.value,
                round_cap=run.round_cap,
                snapshot=payload,
                updated_at=datetime.now(tz=UTC),
            )
            statement = statement.on_conflict_do_update(
                index_elements=[NegotiationRunRow.id],
                set_={
                    "phase": run.phase.value,
                    "round_cap": run.round_cap,
                    "snapshot": payload,
                    "updated_at": datetime.now(tz=UTC),
                },
            )
            await session.execute(statement)
            await session.commit()


class SqlAlchemyRunEventLog:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def append(self, run_id: RunId, events: Sequence[DomainEvent]) -> Sequence[LoggedEvent]:
        if not events:
            return []
        async with self._session_factory() as session:
            lock_key = int.from_bytes(
                hashlib.sha256(str(run_id).encode()).digest()[:8], "big", signed=True
            )
            await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
            current = await session.scalar(
                select(func.max(NegotiationEventRow.sequence)).where(
                    NegotiationEventRow.run_id == str(run_id)
                )
            )
            start = int(current or 0) + 1
            occurred = datetime.now(tz=UTC)
            logged = [
                LoggedEvent(sequence=start + index, event=event, occurred_at=occurred)
                for index, event in enumerate(events)
            ]
            session.add_all(
                [
                    NegotiationEventRow(
                        id=f"evt_{run_id}_{item.sequence}",
                        run_id=str(run_id),
                        sequence=item.sequence,
                        event_type=getattr(item.event, "name", type(item.event).__name__),
                        payload=encode(item.event),
                        occurred_at=item.occurred_at or occurred,
                    )
                    for item in logged
                ]
            )
            await session.commit()
            return logged

    async def read(self, run_id: RunId, until_round: int | None = None) -> Sequence[LoggedEvent]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(NegotiationEventRow)
                    .where(NegotiationEventRow.run_id == str(run_id))
                    .order_by(NegotiationEventRow.sequence)
                )
            ).all()
        logged = [
            LoggedEvent(
                sequence=row.sequence,
                event=decode(row.payload),
                occurred_at=row.occurred_at,
            )
            for row in rows
        ]
        if until_round is None:
            return logged
        bounded: list[LoggedEvent] = []
        for item in logged:
            round_number = getattr(item.event, "round", None)
            if round_number is None:
                round_number = getattr(item.event, "rounds", None)
            if round_number is None or int(round_number) <= until_round:
                bounded.append(item)
        return bounded

    async def latest_sequence(self, run_id: RunId) -> int:
        async with self._session_factory() as session:
            value = await session.scalar(
                select(func.max(NegotiationEventRow.sequence)).where(
                    NegotiationEventRow.run_id == str(run_id)
                )
            )
            return int(value or 0)
