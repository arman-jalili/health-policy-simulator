"""Unit: provider selection and the OpenAI-compatible adapter (#416)."""

from __future__ import annotations

import httpx
import pytest
from tests.conftest import TEST_DATABASE_URL

from shared.config import Settings
from simulation_orchestration.application.errors import LlmProviderFailed
from simulation_orchestration.application.values import LLMRequest, PromptRef
from simulation_orchestration.infrastructure.llm import HttpLlmClient, ScriptedLLMClient


def _request() -> LLMRequest:
    return LLMRequest(
        model="gpt-test",
        prompt="Write a turn",
        prompt_ref=PromptRef("stakeholder-turn", 1),
        parameters={},
    )


def test_scripted_is_refused_outside_local() -> None:
    with pytest.raises(ValueError, match="scripted"):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            env="production",
            auth_mode="strict",
            llm_provider="scripted",
        )


def test_azure_ai_foundry_is_an_accepted_real_provider() -> None:
    settings = Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        llm_provider="azure_ai_foundry",
        llm_base_url="https://example.services.ai.azure.com/openai/v1",
        llm_api_key="secret",
        llm_model="gpt-5-mini",
    )

    assert settings.llm_provider == "azure_ai_foundry"


def test_real_provider_requires_key_and_base_url() -> None:
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            llm_provider="openai-compatible",
        )


async def test_http_adapter_records_provider_usage_and_latency() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={
                "model": "gpt-test",
                "choices": [{"message": {"content": "Institution supports the measure."}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            },
        )

    client = HttpLlmClient(
        model_id="gpt-test",
        base_url="https://llm.example/v1",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    response = await client.complete(_request())

    assert response.text == "Institution supports the measure."
    assert (response.input_tokens, response.output_tokens) == (11, 7)
    assert response.latency_ms >= 0


async def test_http_adapter_retries_then_fails_with_a_named_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, text="upstream down")

    client = HttpLlmClient(
        model_id="gpt-test",
        base_url="https://llm.example/v1",
        api_key="secret",
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LlmProviderFailed, match="http_503"):
        await client.complete(_request())
    assert calls == 3


async def test_scripted_adapter_is_still_available_for_local_tests() -> None:
    client = ScriptedLLMClient("scripted-local")
    response = await client.complete(_request())
    assert "stakeholder-turn@1" in response.text
