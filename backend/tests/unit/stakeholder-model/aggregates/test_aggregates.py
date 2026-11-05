"""Contract freeze: aggregate roots and their command surface (ADR-008)."""

from __future__ import annotations

import dataclasses
import inspect

from tests.unit.stakeholder_contract_helpers import field_names, method_names

from stakeholder_model.domain.agent_binding import AgentBinding
from stakeholder_model.domain.stakeholder import Stakeholder, StakeholderProfile


def test_stakeholder_is_the_aggregate_root() -> None:
    assert Stakeholder.__module__ == "stakeholder_model.domain.stakeholder"
    assert field_names(Stakeholder) == [
        "id",
        "identity",
        "profile",
        "veto_rights",
        "dependencies",
        "history",
        "events",
    ]
    assert dataclasses.is_dataclass(Stakeholder)


def test_stakeholder_owns_the_command_surface() -> None:
    methods = method_names(Stakeholder)

    assert {
        "register_interest",
        "declare_constraint",
        "activate",
        "cite_power_source",
        "record_historical_position",
        "negotiating_power",
        "drain_events",
    } <= methods
    assert not inspect.iscoroutinefunction(Stakeholder.cite_power_source)


def test_profile_is_part_of_the_stakeholder_aggregate() -> None:
    assert StakeholderProfile.__module__ == "stakeholder_model.domain.stakeholder"
    assert field_names(StakeholderProfile) == [
        "mandate_scope",
        "budget",
        "interests",
        "constraints",
        "priorities",
        "red_lines",
        "version",
    ]
    assert {"is_complete", "add_interest", "declare_constraint"} <= method_names(StakeholderProfile)


def test_agent_binding_is_a_separate_aggregate_root() -> None:
    assert AgentBinding.__module__ == "stakeholder_model.domain.agent_binding"
    assert field_names(AgentBinding) == [
        "id",
        "run_id",
        "stakeholder_id",
        "persona_version",
        "allowed_evidence_tiers",
        "red_lines",
    ]
    assert "assert_institution_only" in method_names(AgentBinding)
