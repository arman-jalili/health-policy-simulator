"""The vendor variable is the default, not a second source of truth (DeepSeek live demo)."""

from __future__ import annotations

import pytest

from shared.config import Settings
from tests.conftest import TEST_DATABASE_URL


@pytest.fixture(autouse=True)
def _clear_vendor_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)


def test_deepseek_api_key_is_adopted_when_the_generic_variable_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-vendor-key")

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        llm_provider="openai-compatible",
        llm_base_url="https://api.deepseek.com",
    )

    assert settings.llm_api_key == "sk-vendor-key"


def test_explicit_llm_api_key_wins_over_the_vendor_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-vendor-key")

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        llm_provider="openai-compatible",
        llm_base_url="https://api.deepseek.com",
        llm_api_key="sk-explicit",
    )

    assert settings.llm_api_key == "sk-explicit"


def test_a_real_provider_still_requires_some_key(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            llm_provider="openai-compatible",
            llm_base_url="https://api.deepseek.com",
        )
