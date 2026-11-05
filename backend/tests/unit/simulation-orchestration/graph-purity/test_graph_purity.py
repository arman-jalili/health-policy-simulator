"""Contract freeze: graph purity (issue #205)."""

from __future__ import annotations

import inspect

from tests.unit.simulation_orchestration_contract_helpers import (
    SRC,
    imported_modules,
    method_names,
    parameter_names,
    source,
)

from simulation_orchestration.application.ports import (
    GraphNode,
    NegotiationGateway,
    WorkflowGraph,
)


def test_service_depth_has_no_domain_modules() -> None:
    domain_modules = [path for path in (SRC / "domain").glob("*.py") if path.name != "__init__.py"]
    assert domain_modules == []


def test_graph_nodes_return_state_instead_of_mutating_domain_objects() -> None:
    assert method_names(GraphNode) == {"execute"}
    assert parameter_names(GraphNode.execute) == ["self", "state"]
    assert "GraphState" in str(inspect.signature(GraphNode.execute).return_annotation)


def test_graph_exposes_pure_step_and_next_node() -> None:
    assert method_names(WorkflowGraph) == {"next_node", "step"}


def test_graph_talks_to_negotiation_only_through_commands() -> None:
    assert method_names(NegotiationGateway) == {"close_run", "load_state", "take_turn"}


def test_application_does_not_import_negotiation_domain_internals() -> None:
    for path in (SRC / "application").glob("*.py"):
        modules = imported_modules(str(path.relative_to(SRC)))
        assert not any(module.startswith("negotiation_session.domain") for module in modules)
        assert not any(module.startswith("stakeholder_model.domain") for module in modules)


# --- behaviour: pure sequencing graph and architecture test (issue #206) ---------------------

import ast  # noqa: E402
from dataclasses import replace  # noqa: E402

import pytest  # noqa: E402

from simulation_orchestration.application.values import (  # noqa: E402
    BudgetUsage,
    GraphState,
    RunId,
    RunPhase,
)
from simulation_orchestration.infrastructure.graph import SequentialWorkflowGraph  # noqa: E402


class _Node:
    def __init__(self, name: str, phase: RunPhase) -> None:
        self.name = name
        self.phase = phase
        self.calls = 0

    async def execute(self, state: GraphState) -> GraphState:
        self.calls += 1
        return replace(state, round=state.round + 1)


def _state(phase: RunPhase = RunPhase.ROUNDS) -> GraphState:
    return GraphState(
        run_id=RunId("run_1"),
        round=0,
        phase=phase,
        next_actor="oegk",
        budget_used=BudgetUsage(),
    )


async def test_graph_returns_new_state_and_never_mutates_the_input() -> None:
    node = _Node("take-turn", RunPhase.ROUNDS)
    graph = SequentialWorkflowGraph([node])
    state = _state()

    result = await graph.step("take-turn", state)

    assert result.round == 1
    assert state.round == 0
    assert node.calls == 1


def test_graph_selects_node_by_phase_and_stops_when_done() -> None:
    rounds = _Node("take-turn", RunPhase.ROUNDS)
    close = _Node("close", RunPhase.CLOSE)
    graph = SequentialWorkflowGraph([rounds, close])

    assert graph.next_node(_state(RunPhase.ROUNDS)) == "take-turn"
    assert graph.next_node(_state(RunPhase.CLOSE)) == "close"
    assert graph.next_node(_state(RunPhase.DONE)) is None


def test_graph_rejects_duplicate_or_empty_node_sets() -> None:
    with pytest.raises(ValueError, match="at least one"):
        SequentialWorkflowGraph([])
    with pytest.raises(ValueError, match="unique"):
        SequentialWorkflowGraph([_Node("same", RunPhase.OPEN), _Node("same", RunPhase.CLOSE)])


async def test_unknown_node_is_rejected() -> None:
    graph = SequentialWorkflowGraph([_Node("take-turn", RunPhase.ROUNDS)])

    with pytest.raises(KeyError, match="unknown graph node"):
        await graph.step("missing", _state())


def test_graph_module_cannot_mutate_state_or_import_domain_contexts() -> None:
    tree = ast.parse(source("infrastructure/graph.py"))
    imported = imported_modules("infrastructure/graph.py")

    assert not any(name.startswith("negotiation_session.") for name in imported)
    assert not any(name.startswith("stakeholder_model.") for name in imported)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                    assert target.value.id != "state", "graph nodes must not mutate state"
