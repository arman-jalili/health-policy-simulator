"""Contract freeze: provider independence (issue #205)."""

from __future__ import annotations

from tests.unit.simulation_orchestration_contract_helpers import (
    SRC,
    field_names,
    imported_modules,
    method_names,
)

from simulation_orchestration.application.ports import LLMClient, PriceTable
from simulation_orchestration.application.values import LLMRequest, LLMResponse, ModelPrice


def test_llm_port_is_provider_neutral() -> None:
    assert method_names(LLMClient) == {"complete"}
    assert field_names(LLMRequest) == [
        "model",
        "prompt",
        "prompt_ref",
        "parameters",
        "evidence_pack_ids",
    ]
    assert field_names(LLMResponse) == [
        "text",
        "model",
        "input_tokens",
        "output_tokens",
        "latency_ms",
    ]


def test_prices_are_a_port_not_an_import() -> None:
    assert method_names(PriceTable) == {"price_for"}
    assert field_names(ModelPrice) == ["model_id", "input_per_1k", "output_per_1k"]


def test_application_never_imports_infrastructure() -> None:
    for path in (SRC / "application").glob("*.py"):
        modules = imported_modules(str(path.relative_to(SRC)))
        assert not any(
            module.startswith("simulation_orchestration.infrastructure") for module in modules
        )


def test_repository_boundary_reexports_the_ports() -> None:
    modules = imported_modules("infrastructure/repository/ports.py")
    assert "simulation_orchestration.application.repositories" in modules
