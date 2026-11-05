"""Contract freeze: prompt versioning (issue #205)."""

from __future__ import annotations

from tests.unit.simulation_orchestration_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from simulation_orchestration.application.dto import PromptTemplateResult
from simulation_orchestration.application.errors import PromptNotFound
from simulation_orchestration.application.repositories import PromptRegistry
from simulation_orchestration.application.rules import PromptVersioning
from simulation_orchestration.application.services import (
    RegisterPromptTemplate,
    ResolvePromptTemplate,
)
from simulation_orchestration.application.values import PromptRef, PromptTemplate


def test_prompt_template_is_append_only() -> None:
    assert field_names(PromptTemplate) == [
        "id",
        "name",
        "version",
        "body",
        "checksum",
        "created_at",
    ]
    assert field_names(PromptTemplateResult) == field_names(PromptTemplate)
    assert PromptRef("policy", 2).identity == "policy@2"


def test_registry_supports_latest_and_explicit_versions() -> None:
    assert method_names(PromptRegistry) == {
        "get",
        "latest",
        "list_versions",
        "register",
    }
    assert parameter_names(ResolvePromptTemplate.execute) == ["self", "request"]
    assert parameter_names(RegisterPromptTemplate.execute) == ["self", "request"]


def test_versioning_creates_a_new_version_for_a_new_body() -> None:
    assert method_names(PromptVersioning) == {"next_version"}
    assert parameter_names(PromptVersioning.next_version) == [
        "self",
        "existing",
        "name",
        "body",
    ]
    assert PromptNotFound.code == "PROMPT_NOT_FOUND"
