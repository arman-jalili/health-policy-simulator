"""Contract freeze: demo mode is local-only and cannot boot in production."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from identity_access.interfaces.ports import DemoModePolicy
from shared.config import Settings
from shared.enums import AuthMode, Environment, Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def test_demo_mode_is_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="AUTH_MODE=demo"):
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            env=Environment.PRODUCTION,
            auth_mode=AuthMode.DEMO,
            persistence=Persistence.MEMORY,
        )


def test_demo_policy_is_a_port_with_a_localhost_predicate() -> None:
    assert hasattr(DemoModePolicy, "permits")
