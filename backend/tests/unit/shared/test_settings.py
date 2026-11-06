"""Configuration contract: fail fast, never run demo auth in production (ADR-005)."""

from __future__ import annotations

import pytest

from shared.config import ConfigError, Settings, load_settings
from shared.enums import AuthMode, Environment, Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def test_missing_database_url_fails_fast() -> None:
    with pytest.raises(ConfigError, match="DATABASE_URL"):
        load_settings(_env_file=None)


def test_minimal_configuration_is_valid() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL)

    assert settings.env is Environment.LOCAL
    assert settings.auth_mode is AuthMode.DEMO
    assert settings.is_demo
    assert settings.api_prefix == "/api/v1"


def test_demo_mode_is_refused_in_production() -> None:
    with pytest.raises(ConfigError, match="AUTH_MODE=demo"):
        load_settings(
            _env_file=None,
            database_url=DATABASE_URL,
            env="production",
            auth_mode="demo",
        )


def test_strict_mode_is_allowed_in_production() -> None:
    settings = load_settings(
        _env_file=None,
        database_url=DATABASE_URL,
        env="production",
        auth_mode="strict",
        llm_provider="openai-compatible",
        llm_base_url="https://llm.example/v1",
        llm_api_key="test-key",
    )

    assert not settings.is_demo


def test_invalid_database_url_is_rejected() -> None:
    with pytest.raises(ConfigError):
        load_settings(_env_file=None, database_url="not-a-dsn")


def test_secrets_are_not_rendered() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL)

    assert "hps:hps" not in repr(settings)


class TestPersistenceConfiguration:
    def test_postgres_is_the_default(self) -> None:
        settings = Settings(_env_file=None, database_url=DATABASE_URL)

        assert settings.persistence is Persistence.POSTGRES

    def test_memory_is_available_for_a_database_less_demo(self) -> None:
        settings = load_settings(
            _env_file=None,
            database_url=DATABASE_URL,
            persistence="memory",
        )

        assert settings.persistence is Persistence.MEMORY

    @pytest.mark.parametrize("environment", ["staging", "production"])
    def test_memory_is_refused_outside_local(self, environment: str) -> None:
        with pytest.raises(ConfigError, match="PERSISTENCE=memory"):
            load_settings(
                _env_file=None,
                database_url=DATABASE_URL,
                env=environment,
                auth_mode="strict",
                persistence="memory",
                llm_provider="openai-compatible",
                llm_base_url="https://llm.example/v1",
                llm_api_key="test-key",
            )
