"""Ports and framework-free collaborator contracts (contract frozen, issue #205)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Protocol, runtime_checkable

from simulation_orchestration.application.events import SimulationEvent
from simulation_orchestration.application.values import (
    GraphState,
    LLMRequest,
    LLMResponse,
    ModelPrice,
    NegotiationRunView,
    NegotiationTurnBriefing,
    NegotiationTurnCommand,
    NegotiationTurnView,
    RunId,
    RunPhase,
)


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class UnitOfWork(Protocol):
    def transaction(self) -> AbstractAsyncContextManager[object]: ...


@runtime_checkable
class PriceTable(Protocol):
    """Model price lookup. Unknown ids raise ``UnknownModel`` at boot and pre-call."""

    def price_for(self, model_id: str) -> ModelPrice: ...


@runtime_checkable
class LLMClient(Protocol):
    """Provider-independent completion port. Only ``infrastructure/`` implements it."""

    model_id: str

    async def complete(self, request: LLMRequest) -> LLMResponse: ...


@runtime_checkable
class LlmProviderControl(Protocol):
    """Runtime view and switch for the model backend (demo: show both variations live)."""

    def active(self) -> str: ...

    def active_model(self) -> str: ...

    def available(self) -> tuple[str, ...]: ...

    def switch(self, provider: str) -> None: ...


@runtime_checkable
class GraphNode(Protocol):
    """One sequencing step. It receives and returns state; it never mutates domain state."""

    name: str
    phase: RunPhase

    async def execute(self, state: GraphState) -> GraphState: ...


@runtime_checkable
class WorkflowGraph(Protocol):
    """Pure sequencing surface around the provider graph implementation."""

    def next_node(self, state: GraphState) -> str | None: ...

    async def step(self, node_name: str, state: GraphState) -> GraphState: ...


@runtime_checkable
class NegotiationGateway(Protocol):
    """ACL to NegotiationSession. The graph calls commands; it never reads aggregates."""

    async def load_state(self, run_id: RunId) -> NegotiationRunView: ...

    async def briefing(self, run_id: RunId, actor_id: str) -> NegotiationTurnBriefing: ...

    async def take_turn(self, command: NegotiationTurnCommand) -> NegotiationTurnView: ...

    async def close_run(self, run_id: RunId) -> None: ...


@runtime_checkable
class EventPublisher(Protocol):
    async def publish(self, events: Sequence[SimulationEvent]) -> None: ...


@runtime_checkable
class WorkerLoop(Protocol):
    """Background worker started by the app lifespan or a compose companion."""

    async def run_forever(self, stop: asyncio.Event) -> None: ...

    async def run_supervised(self, stop: asyncio.Event) -> None:
        """Keep the loop alive across unexpected infrastructure failures."""
        ...

    async def run_once(self) -> bool: ...

    async def recover(self) -> int:
        """Re-queue RUNNING jobs left behind by a dead worker; return the resumable count."""
        ...


@runtime_checkable
class ProgressStream(Protocol):
    def __aiter__(self) -> AsyncIterator[object]: ...
