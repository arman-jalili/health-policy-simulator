"""Contract freeze: prompt versioning (issue #205)."""

from __future__ import annotations

from datetime import UTC, datetime

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
        "save",
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


# --- behaviour: append-only prompt versions (issue #214) -----------------------------------

import pytest  # noqa: E402

from simulation_orchestration.application.commands import (  # noqa: E402
    RegisterPromptTemplateRequest,
    ResolvePromptTemplateRequest,
)
from simulation_orchestration.infrastructure.memory import (  # noqa: E402
    InMemoryPromptRegistry,
)


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


def _register_service() -> tuple[RegisterPromptTemplate, InMemoryPromptRegistry]:
    registry = InMemoryPromptRegistry()
    return (
        RegisterPromptTemplate(registry=registry, versioning=PromptVersioning(), clock=_Clock()),
        registry,
    )


async def test_changed_body_creates_a_new_version_and_old_body_is_unchanged() -> None:
    service, registry = _register_service()

    first = await service.execute(RegisterPromptTemplateRequest("policy", "body one"))
    second = await service.execute(RegisterPromptTemplateRequest("policy", "body two"))

    assert first.version == 1
    assert second.version == 2
    assert first.checksum != second.checksum
    assert (await registry.get("policy", 1)).body == "body one"  # type: ignore[union-attr]


async def test_identical_body_reuses_the_latest_version() -> None:
    service, _ = _register_service()

    first = await service.execute(RegisterPromptTemplateRequest("policy", "same"))
    again = await service.execute(RegisterPromptTemplateRequest("policy", "same"))

    assert again.version == first.version


async def test_old_invocations_keep_their_prompt_version() -> None:
    service, _ = _register_service()
    old = await service.execute(RegisterPromptTemplateRequest("policy", "v1"))
    await service.execute(RegisterPromptTemplateRequest("policy", "v2"))

    assert PromptRef("policy", old.version).identity == "policy@1"


async def test_resolve_latest_and_explicit_version() -> None:
    registry = InMemoryPromptRegistry()
    register = RegisterPromptTemplate(
        registry=registry,
        versioning=PromptVersioning(),
        clock=_Clock(),
    )
    resolve = ResolvePromptTemplate(registry=registry)
    await register.execute(RegisterPromptTemplateRequest("policy", "one"))
    await register.execute(RegisterPromptTemplateRequest("policy", "two"))

    latest = await resolve.execute(ResolvePromptTemplateRequest("policy"))
    explicit = await resolve.execute(ResolvePromptTemplateRequest("policy", version=1))

    assert latest.version == 2
    assert explicit.body == "one"


async def test_unknown_prompt_and_empty_body_fail_closed() -> None:
    registry = InMemoryPromptRegistry()
    resolve = ResolvePromptTemplate(registry=registry)

    with pytest.raises(PromptNotFound):
        await resolve.execute(ResolvePromptTemplateRequest("missing"))
    with pytest.raises(ValueError, match="body must not be empty"):
        PromptVersioning().next_version(existing=[], name="policy", body="  ")
