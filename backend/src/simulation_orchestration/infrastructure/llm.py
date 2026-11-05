"""Provider adapters for the frozen LLM port (issue #215).

Canonical: .pi/architecture/modules/simulation-orchestration.md

The application layer depends only on ``LLMClient``. Swapping providers is an infrastructure
change; this module is the only place that knows a concrete provider/model behaviour.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping

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
