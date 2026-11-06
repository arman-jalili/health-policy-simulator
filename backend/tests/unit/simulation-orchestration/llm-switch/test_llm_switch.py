"""Runtime model switch: the demo shows the live model and the scripted stand-in live."""

from __future__ import annotations

import httpx
import pytest
from tests.conftest import TEST_DATABASE_URL

from shared.config import Settings
from simulation_orchestration.application.commands import SelectLlmProviderRequest
from simulation_orchestration.application.errors import UnknownLlmProvider
from simulation_orchestration.application.services import GetLlmProvider, SelectLlmProvider
from simulation_orchestration.application.values import LLMRequest, PromptRef
from simulation_orchestration.infrastructure.llm import (
    HttpLlmClient,
    ScriptedLLMClient,
    SwitchableLlmClient,
)


def _request() -> LLMRequest:
    return LLMRequest(
        model="",
        prompt="Write a turn",
        prompt_ref=PromptRef("stakeholder-turn", 1),
        parameters={},
    )


def _switchable() -> SwitchableLlmClient:
    live = HttpLlmClient(
        model_id="vendor-model",
        base_url="https://llm.example/v1",
        api_key="sk-test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "model": "vendor-model",
                    "choices": [{"message": {"role": "assistant", "content": "live text"}}],
                    "usage": {"prompt_tokens": 4, "completion_tokens": 2},
                },
            )
        ),
    )
    return SwitchableLlmClient(
        {"openai-compatible": live, "scripted": ScriptedLLMClient("scripted-local")},
        active="openai-compatible",
    )


async def test_switching_changes_which_adapter_answers_and_what_usage_says() -> None:
    client = _switchable()

    live = await client.complete(_request())
    assert live.text == "live text"
    assert live.model == "vendor-model"

    client.switch("scripted")
    scripted = await client.complete(_request())
    assert "stakeholder-turn@1" in scripted.text
    assert scripted.model == "scripted-local"

    assert client.active() == "scripted"
    assert client.model_id == "scripted-local"
    assert client.available() == ("openai-compatible", "scripted")


async def test_unknown_variant_is_refused_with_the_configured_names() -> None:
    client = _switchable()

    with pytest.raises(UnknownLlmProvider, match="openai-compatible"):
        client.switch("vendor-unknown")


def test_switching_to_the_active_variant_is_a_no_op() -> None:
    client = _switchable()

    client.switch("openai-compatible")

    assert client.active() == "openai-compatible"


def test_services_expose_and_apply_the_switch() -> None:
    client = _switchable()

    read = GetLlmProvider(control=client).execute()
    assert read.active == "openai-compatible"
    assert read.model == "vendor-model"
    assert set(read.available) == {"openai-compatible", "scripted"}

    switched = SelectLlmProvider(control=client).execute(
        SelectLlmProviderRequest(provider="scripted")
    )
    assert switched.active == "scripted"
    assert switched.model == "scripted-local"


def test_only_scripted_is_available_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The compose default: no key, so the live variant does not exist and cannot be selected."""
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        persistence="memory",
        llm_provider="scripted",
    )
    assert settings.llm_api_key is None
