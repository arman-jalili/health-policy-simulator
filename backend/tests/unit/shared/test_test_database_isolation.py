"""Unit: destructive integration fixtures refuse a non-test database (#421)."""

from __future__ import annotations

import pytest

from tests import conftest


def test_default_test_database_is_derived_from_the_configured_one() -> None:
    derived = conftest._test_database_url(
        "postgresql+asyncpg://hps:hps@localhost:5433/health_policy?ssl=disable"
    )

    assert derived == "postgresql+asyncpg://hps:hps@localhost:5433/health_policy_test?ssl=disable"


async def test_non_test_database_is_refused_before_any_destructive_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_TESTS", raising=False)
    monkeypatch.setattr(
        conftest,
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://hps:hps@localhost:5433/health_policy",
    )

    with pytest.raises(RuntimeError, match="refusing destructive integration tests"):
        await conftest._ensure_test_database()
