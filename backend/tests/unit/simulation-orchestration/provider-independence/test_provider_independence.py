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


# --- behaviour: swapping adapters is an infrastructure change (issue #215) ------------------

import pytest  # noqa: E402

from simulation_orchestration.application.values import (  # noqa: E402
    PromptRef,
)
from simulation_orchestration.infrastructure.llm import (  # noqa: E402
    MappedLLMClient,
    ScriptedLLMClient,
)


def _request() -> LLMRequest:
    return LLMRequest(
        model="model-a",
        prompt="Take the turn",
        prompt_ref=PromptRef("take-turn", 1),
        parameters={},
    )


async def test_scripted_adapter_returns_a_complete_response_envelope() -> None:
    response = await ScriptedLLMClient("model-a").complete(_request())

    assert response.model == "model-a"
    assert response.text.startswith("[take-turn@1]")
    assert response.input_tokens >= 1
    assert response.output_tokens >= 1


async def test_two_providers_satisfy_the_same_port_without_application_changes() -> None:
    scripted = ScriptedLLMClient("model-a")
    mapped = MappedLLMClient("model-b", {"take-turn@1": "provider b answer"})

    one = await scripted.complete(_request())
    two = await mapped.complete(_request())

    assert one.model == "model-a"
    assert two.model == "model-b"
    assert two.text == "provider b answer"


async def test_provider_error_is_propagated_for_retry_policy() -> None:
    async def explode(request: LLMRequest) -> str:
        raise RuntimeError(f"provider failed for {request.prompt_ref.identity}")

    with pytest.raises(RuntimeError, match="provider failed"):
        await ScriptedLLMClient("model-a", completion=explode).complete(_request())


def test_provider_sdk_imports_are_absent_from_application() -> None:
    forbidden = ("openai", "anthropic", "httpx", "boto3")
    for path in (SRC / "application").glob("*.py"):
        modules = imported_modules(str(path.relative_to(SRC)))
        assert not any(module.split(".")[0] in forbidden for module in modules)
