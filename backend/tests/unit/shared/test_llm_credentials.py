"""One generic credential for any OpenAI-compatible provider; no vendor fallback."""

from __future__ import annotations

import pytest

from shared.config import Settings
from tests.conftest import TEST_DATABASE_URL


@pytest.fixture(autouse=True)
def _no_ambient_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)


def test_the_key_comes_from_the_generic_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-generic")

    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        llm_provider="openai-compatible",
        llm_base_url="https://llm.example/v1",
    )

    assert settings.llm_api_key == "sk-generic"


def test_any_key_works_regardless_of_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two different endpoints, one credential path — nothing is vendor-specific."""
    monkeypatch.setenv("LLM_API_KEY", "local-token")

    for base_url in ("https://api.openai.com/v1", "http://ollama:11434/v1"):
        settings = Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            llm_provider="openai-compatible",
            llm_base_url=base_url,
        )
        assert settings.llm_api_key == "local-token"


def test_a_real_provider_still_requires_a_key() -> None:
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            llm_provider="openai-compatible",
            llm_base_url="https://llm.example/v1",
        )
