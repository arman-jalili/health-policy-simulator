"""Unit of work: one ambient transaction, or a self-committing short scope."""

from __future__ import annotations

from typing import Any

import pytest

from shared.db import UnitOfWork


class FakeSession:
    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        self.rolled_back += 1

    def begin(self) -> Any:
        return self

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class FakeSessionFactory:
    def __init__(self) -> None:
        self.sessions: list[FakeSession] = []

    def __call__(self) -> Any:
        session = FakeSession()
        self.sessions.append(session)
        return session


def build_unit_of_work() -> tuple[UnitOfWork, FakeSessionFactory]:
    factory = FakeSessionFactory()
    return UnitOfWork(factory), factory  # type: ignore[arg-type]


async def test_operations_outside_a_transaction_commit_their_own_scope() -> None:
    unit_of_work, factory = build_unit_of_work()

    async with unit_of_work.session():
        assert not unit_of_work.has_active_transaction

    assert factory.sessions[0].committed == 1


async def test_every_operation_joins_the_ambient_transaction() -> None:
    unit_of_work, factory = build_unit_of_work()

    async with unit_of_work.transaction() as outer:
        assert unit_of_work.has_active_transaction
        async with unit_of_work.session() as first:
            assert first is outer
        async with unit_of_work.session() as second:
            assert second is outer
        assert factory.sessions[0].committed == 0

    assert factory.sessions[0].committed == 1
    assert unit_of_work.has_active_transaction is False


async def test_nested_transactions_do_not_commit_early() -> None:
    unit_of_work, factory = build_unit_of_work()

    async with unit_of_work.transaction() as outer, unit_of_work.transaction() as nested:
        assert nested is outer

    assert factory.sessions[0].committed == 1


async def test_failure_rolls_back_the_ambient_transaction() -> None:
    unit_of_work, factory = build_unit_of_work()

    with pytest.raises(RuntimeError, match="boom"):
        async with unit_of_work.transaction():
            raise RuntimeError("boom")

    assert factory.sessions[0].rolled_back == 1
    assert factory.sessions[0].committed == 0


async def test_context_is_cleared_after_a_failure() -> None:
    unit_of_work, _ = build_unit_of_work()

    with pytest.raises(RuntimeError):
        async with unit_of_work.transaction():
            raise RuntimeError

    assert unit_of_work.has_active_transaction is False
