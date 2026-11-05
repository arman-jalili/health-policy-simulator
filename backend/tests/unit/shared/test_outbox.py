"""Outbox and audit writers: transaction participation, not transaction ownership."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.audit import AuditWriter
from shared.clock import FixedClock
from shared.enums import AuditOutcome, OutboxStatus
from shared.outbox import OutboxMessage, OutboxWriter


class RecordingSession:
    """Minimal session double: records added rows, commits nothing."""

    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, row: Any) -> None:
        self.added.append(row)


def _session(session: RecordingSession) -> AsyncSession:
    return cast(AsyncSession, session)


async def test_write_adds_pending_row_in_caller_transaction(fixed_clock: FixedClock) -> None:
    session = RecordingSession()
    writer = OutboxWriter(clock=fixed_clock)

    event = await writer.write(
        _session(session),
        event_name="DocumentIngested",
        aggregate_type="Document",
        aggregate_id="doc_01J0000000000000000000000A",
        payload={"document_id": "doc_01J0000000000000000000000A", "pages": 12},
        actor="operator:demo",
        trace_id="req_01J0000000000000000000000B",
    )

    assert len(session.added) == 1
    row = cast(OutboxMessage, session.added[0])
    assert isinstance(row, OutboxMessage)
    assert row.id == event.event_id
    assert row.status == OutboxStatus.PENDING.value
    assert row.occurred_at == fixed_clock.now()
    assert row.payload == {"document_id": "doc_01J0000000000000000000000A", "pages": 12}
    assert row.actor == "operator:demo"
    assert row.trace_id == "req_01J0000000000000000000000B"


async def test_payload_schema_version_is_persisted(fixed_clock: FixedClock) -> None:
    session = RecordingSession()

    event = await OutboxWriter(clock=fixed_clock).write(
        _session(session),
        event_name="PassageIndexed",
        aggregate_type="Passage",
        aggregate_id="psg_01J0000000000000000000000C",
        payload={},
        actor="system",
        payload_schema_version=3,
    )

    assert event.payload_schema_version == 3
    assert cast(OutboxMessage, session.added[0]).payload_schema_version == 3


async def test_non_serialisable_payload_is_rejected() -> None:
    writer = OutboxWriter()

    with pytest.raises(ValueError, match="JSON-serialisable"):
        await writer.write(
            _session(RecordingSession()),
            event_name="Broken",
            aggregate_type="Thing",
            aggregate_id="thing_1",
            payload={"when": datetime(2026, 11, 5, 9, 0)},
            actor="system",
        )


def test_event_names_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match="event_name"):
        OutboxWriter().build(
            event_name="",
            aggregate_type="Thing",
            aggregate_id="thing_1",
            payload={},
            actor="system",
        )


async def test_audit_writer_records_outcome_and_details(fixed_clock: FixedClock) -> None:
    session = RecordingSession()

    record = await AuditWriter(clock=fixed_clock).record(
        _session(session),
        action="brief.publish",
        actor="analyst:demo",
        resource_type="DecisionBrief",
        resource_id="brf_01J0000000000000000000000D",
        outcome=AuditOutcome.REFUSED,
        details={"reason": "CitationResolutionFailed"},
        trace_id="req_01J0000000000000000000000E",
    )

    assert session.added == [record]
    assert record.outcome == AuditOutcome.REFUSED.value
    assert record.details == {"reason": "CitationResolutionFailed"}
    assert record.id.startswith("aud_")
