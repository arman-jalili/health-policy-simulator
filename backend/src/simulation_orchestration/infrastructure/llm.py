"""Provider adapters for the frozen LLM port (issue #215).

Canonical: .pi/architecture/modules/simulation-orchestration.md

The application layer depends only on ``LLMClient``. Swapping providers is an infrastructure
change; this module is the only place that knows a concrete provider/model behaviour.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping

import httpx

from simulation_orchestration.application.errors import LlmProviderFailed
from simulation_orchestration.application.values import LLMRequest, LLMResponse

Completion = Callable[[LLMRequest], Awaitable[str]]


class ScriptedLLMClient:
    """Deterministic adapter for CI, local runs and provider-swap tests."""

    def __init__(self, model_id: str, completion: Completion | None = None) -> None:
        self.model_id = model_id
        self._completion = completion or self._default_completion

    async def complete(self, request: LLMRequest) -> LLMResponse:
        text = await self._completion(request)
        words = len(text.split())
        return LLMResponse(
            text=text,
            model=self.model_id,
            input_tokens=max(1, len(request.prompt) // 4),
            output_tokens=max(1, words),
            latency_ms=0,
        )

    @staticmethod
    async def _default_completion(request: LLMRequest) -> str:
        return f"[{request.prompt_ref.identity}] {request.prompt}"


class HttpLlmClient:
    """OpenAI-compatible ``/chat/completions`` adapter with bounded retries and real usage."""

    def __init__(
        self,
        *,
        model_id: str,
        base_url: str,
        api_key: str,
        timeout_s: float = 30.0,
        max_retries: int = 2,
        temperature: float = 0.2,
        max_output_tokens: int = 1024,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model_id = model_id
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._transport = transport

    async def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": request.model or self.model_id,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": self._temperature,
            "max_tokens": self._max_output_tokens,
        }
        started = time.perf_counter()
        last_error = "provider returned no response"
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout_s, transport=self._transport
                ) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "api-key": self._api_key,
                        },
                        json=payload,
                    )
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last_error = f"{type(error).__name__}: {error}"
            else:
                if response.is_success:
                    return self._parse(response, request, started)
                last_error = f"http_{response.status_code}: {response.text[:300]}"
                if response.status_code not in {429, 500, 502, 503, 504}:
                    break
            if attempt < self._max_retries:
                await asyncio.sleep(0.05 * (2**attempt))
        raise LlmProviderFailed(f"LLM provider failed after retries: {last_error}")

    def _parse(self, response: httpx.Response, request: LLMRequest, started: float) -> LLMResponse:
        body = response.json()
        choices = body.get("choices") or []
        if not choices:
            raise LlmProviderFailed("LLM provider returned no choices")
        text = str((choices[0].get("message") or {}).get("content") or "")
        usage = body.get("usage") or {}
        return LLMResponse(
            text=text,
            model=str(body.get("model") or request.model),
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )


class MappedLLMClient(ScriptedLLMClient):
    """Scripted adapter keyed by ``prompt@version`` for deterministic scenarios."""

    def __init__(self, model_id: str, responses: Mapping[str, str]) -> None:
        super().__init__(model_id, completion=None)
        self._responses = dict(responses)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        text = self._responses.get(request.prompt_ref.identity, request.prompt)
        words = len(text.split())
        return LLMResponse(
            text=text,
            model=self.model_id,
            input_tokens=max(1, len(request.prompt) // 4),
            output_tokens=max(1, words),
            latency_ms=0,
        )
