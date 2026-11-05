"""Invocation rows are keyed by the logical call, not a random execution id."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from simulation_orchestration.application.services import RecordAgentInvocation
from simulation_orchestration.application.state import initial_state
from simulation_orchestration.application.values import (
    LLMRequest,
    ModelPrice,
    PromptRef,
    RunId,
)
from simulation_orchestration.infrastructure.bootstrap import BootstrapMandateNode
from simulation_orchestration.infrastructure.llm import ScriptedLLMClient
from simulation_orchestration.infrastructure.memory import InMemoryInvocationStore
from simulation_orchestration.infrastructure.pricing import StaticPriceTable


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


def test_same_node_execution_twice_writes_one_invocation() -> None:
    store = InMemoryInvocationStore()
    prices = StaticPriceTable(
        {"scripted-local": ModelPrice("scripted-local", Decimal("0.01"), Decimal("0.02"))}
    )
    recorder = RecordAgentInvocation(invocations=store, prices=prices, clock=_Clock())
    node = BootstrapMandateNode(
        recorder, model="scripted-local", llm=ScriptedLLMClient("scripted-local")
    )
    state = initial_state(RunId("run_idempotent"))

    asyncio.run(node.execute(state))
    asyncio.run(node.execute(state))

    usage = asyncio.run(store.usage_for_run(RunId("run_idempotent")))
    assert usage.invocations == 1


def _request(prompt: str) -> LLMRequest:
    return LLMRequest(model="m", prompt=prompt, prompt_ref=PromptRef("p", 1), parameters={})


def test_tokens_come_from_the_llm_not_literals() -> None:
    client = ScriptedLLMClient("m")
    short = asyncio.run(client.complete(_request("short")))
    long = asyncio.run(client.complete(_request("a much longer prompt with many characters")))

    assert long.input_tokens > short.input_tokens
