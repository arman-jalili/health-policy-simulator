"""PostgreSQL adapter for DecisionBrief (issue #407)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.values import BriefId, RunId
from decision_brief.infrastructure.repository.models import DecisionBriefRow
from decision_brief.infrastructure.repository.serialization import decode_brief, encode_brief


class SqlAlchemyDecisionBriefRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, brief_id: BriefId) -> DecisionBrief | None:
        async with self._session_factory() as session:
            row = await session.get(DecisionBriefRow, str(brief_id))
            return decode_brief(row.snapshot) if row is not None else None

    async def save(self, brief: DecisionBrief) -> None:
        payload = encode_brief(brief)
        async with self._session_factory() as session:
            statement = insert(DecisionBriefRow).values(
                id=str(brief.id),
                run_id=str(brief.run_id),
                version=brief.version.number,
                status=brief.status.value,
                snapshot=payload,
                updated_at=datetime.now(tz=UTC),
            )
            statement = statement.on_conflict_do_update(
                index_elements=[DecisionBriefRow.id],
                set_={"status": brief.status.value, "snapshot": payload},
            )
            await session.execute(statement)
            await session.commit()

    async def versions_for_run(self, run_id: RunId) -> list[DecisionBrief]:
        async with self._session_factory() as session:
            rows = (
                await session.scalars(
                    select(DecisionBriefRow)
                    .where(DecisionBriefRow.run_id == str(run_id))
                    .order_by(DecisionBriefRow.version)
                )
            ).all()
        return [decode_brief(row.snapshot) for row in rows]
