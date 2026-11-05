"""Contract freeze: AgentBinding is immutable and has no update path (ADR-008)."""

from __future__ import annotations

import dataclasses
from typing import Any, cast

import pytest
from tests.unit.stakeholder_contract_helpers import field_names, method_names

from evidence_corpus.domain.values import AuthorityTier
from stakeholder_model.domain.agent_binding import AgentBinding
from stakeholder_model.domain.repositories import AgentBindingRepository
from stakeholder_model.domain.values import (
    BindingId,
    PersonaVersion,
    RunId,
    StakeholderId,
)
from stakeholder_model.interfaces.published import AgentBindingView


def _binding() -> AgentBinding:
    return AgentBinding(
        id=BindingId("bnd_1"),
        run_id=RunId("run_1"),
        stakeholder_id=StakeholderId("stk_1"),
        persona_version=PersonaVersion("v1"),
        allowed_evidence_tiers=frozenset({AuthorityTier.LEGISLATION}),
        red_lines=("no benefit cut",),
    )


def test_binding_cannot_be_mutated_after_construction() -> None:
    binding = _binding()

    with pytest.raises(dataclasses.FrozenInstanceError):
        binding.persona_version = PersonaVersion("v2")  # type: ignore[misc]


def test_repository_has_no_update_or_delete_path() -> None:
    methods = method_names(AgentBindingRepository)

    assert methods == {"get_for_run", "save"}
    assert not {"update", "delete", "replace"} & methods


def test_binding_view_is_also_frozen() -> None:
    assert cast(Any, AgentBindingView).__dataclass_params__.frozen is True
    assert field_names(AgentBindingView) == [
        "binding_id",
        "run_id",
        "stakeholder_id",
        "persona_version",
        "allowed_evidence_tiers",
        "red_lines",
    ]
