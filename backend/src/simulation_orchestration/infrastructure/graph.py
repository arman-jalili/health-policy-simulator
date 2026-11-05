"""Pure sequencing graph (issue #206).

Canonical: .pi/architecture/modules/simulation-orchestration.md

The graph is a sequencer. Nodes receive ``GraphState`` and return the next ``GraphState``; they do
not mutate domain objects or hold negotiation positions/arguments/evidence. Any state change is
performed by an application service through ``NegotiationGateway``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from simulation_orchestration.application.ports import GraphNode
from simulation_orchestration.application.values import GraphState, RunPhase


class SequentialWorkflowGraph:
    """Ordered graph keyed by phase; each step is a pure node invocation."""

    def __init__(self, nodes: Sequence[GraphNode]) -> None:
        if not nodes:
            raise ValueError("a workflow graph needs at least one node")
        by_name = {node.name: node for node in nodes}
        if len(by_name) != len(nodes):
            raise ValueError("graph node names must be unique")
        self._nodes: Mapping[str, GraphNode] = by_name
        self._ordered = tuple(nodes)

    def next_node(self, state: GraphState) -> str | None:
        if state.phase is RunPhase.DONE:
            return None
        for node in self._ordered:
            if node.phase is state.phase:
                return node.name
        return None

    async def step(self, node_name: str, state: GraphState) -> GraphState:
        node = self._nodes.get(node_name)
        if node is None:
            raise KeyError(f"unknown graph node {node_name!r}")
        return await node.execute(state)
