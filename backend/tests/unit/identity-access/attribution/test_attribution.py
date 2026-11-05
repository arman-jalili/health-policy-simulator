"""Attribution: every command event carries the resolved principal's actor label."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from evidence_corpus.domain.events import DocumentIngested
from evidence_corpus.domain.values import ExtractionMethod
from evidence_corpus.infrastructure.events import OutboxEventPublisher
from identity_access.interfaces.types import Principal, Role, Scope
from shared.attribution import actor_scope, current_actor
from shared.outbox import OutboxEvent, OutboxWriter


class RecordingSession:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    def add(self, row: Any) -> None:
        self.rows.append(row)


class RecordingUnitOfWork:
    def __init__(self, session: RecordingSession) -> None:
        self._session = session

    @asynccontextmanager
    async def session(self):  # type: ignore[no-untyped-def]
        yield self._session


def test_principal_label_is_the_actor_id() -> None:
    principal = Principal(
        label="alice",
        role=Role.ANALYST,
        scopes=frozenset({Scope.RUNS_READ}),
    )

    assert principal.actor_id() == "alice"


def test_empty_actor_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="label"):
        Principal(label="   ", role=Role.ANALYST, scopes=frozenset())


def test_actor_scope_sets_and_resets_the_context() -> None:
    assert current_actor() is None

    with actor_scope("alice"):
        assert current_actor() == "alice"

    assert current_actor() is None


def test_empty_actor_scope_is_rejected() -> None:
    with pytest.raises(ValueError, match="actor"), actor_scope("   "):
        pass


def test_outbox_event_rejects_an_empty_actor() -> None:
    with pytest.raises(ValueError, match="actor"):
        OutboxEvent(
            event_name="DocumentIngested",
            aggregate_type="EvidenceCorpus",
            aggregate_id="doc_1",
            payload={},
            actor="   ",
            occurred_at=datetime.now(UTC),
        )


async def test_outbox_publisher_prefers_the_request_actor() -> None:
    session = RecordingSession()
    publisher = OutboxEventPublisher(
        cast(Any, RecordingUnitOfWork(session)),
        OutboxWriter(),
    )
    event = DocumentIngested(
        document_id="doc_1",
        source_uri="file:///tmp/source.pdf",
        content_hash="hash",
        quality_method=ExtractionMethod.NATIVE,
    )

    with actor_scope("alice"):
        await publisher.publish([event], actor="system")

    assert [row.actor for row in session.rows] == ["alice"]
