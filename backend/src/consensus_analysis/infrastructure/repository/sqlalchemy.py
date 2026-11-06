"""PostgreSQL projection repository for ConsensusAnalysis (issue #406)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.values import ConsensusId, RunId
from consensus_analysis.infrastructure.repository.models import ConsensusRecordRow
from consensus_analysis.infrastructure.repository.serialization import decode_record, encode_record


class SqlAlchemyConsensusRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, consensus_id: ConsensusId) -> ConsensusRecord | None:
        async with self._session_factory() as session:
            row = await session.get(ConsensusRecordRow, str(consensus_id))
            return decode_record(row.payload) if row is not None else None

    async def save(self, record: ConsensusRecord) -> None:
        await self.replace_for_run(record.run_id, (record,))

    async def for_run(self, run_id: RunId) -> list[ConsensusRecord]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(ConsensusRecordRow)
                    .where(ConsensusRecordRow.run_id == str(run_id))
                    .order_by(ConsensusRecordRow.log_position)
                )
            ).all()
        return [decode_record(row.payload) for row in rows]

    async def replace_for_run(self, run_id: RunId, records: Sequence[ConsensusRecord]) -> None:
        async with self._session_factory() as session:
            await session.execute(
                delete(ConsensusRecordRow).where(ConsensusRecordRow.run_id == str(run_id))
            )
            for record in records:
                statement = insert(ConsensusRecordRow).values(
                    id=str(record.id),
                    run_id=str(run_id),
                    topic=str(record.topic),
                    log_position=int(record.log_position),
                    payload=encode_record(record),
                    updated_at=datetime.now(tz=UTC),
                )
                await session.execute(
                    statement.on_conflict_do_update(
                        index_elements=[ConsensusRecordRow.id],
                        set_={"payload": statement.excluded.payload},
                    )
                )
            await session.commit()
