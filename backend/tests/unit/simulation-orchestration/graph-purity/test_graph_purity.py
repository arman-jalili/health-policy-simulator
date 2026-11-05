"""Contract freeze: graph purity (issue #205)."""

from __future__ import annotations

import inspect

from tests.unit.simulation_orchestration_contract_helpers import (
    SRC,
    imported_modules,
    method_names,
    parameter_names,
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
