"""Contract freeze: simulation disclaimer (issue #331, implements #342).

A brief without the disclaimer cannot publish; the frozen text is a constant, not a free field.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tests.unit.decision_brief_contract_helpers import field_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.errors import DisclosureMissing
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    BriefId,
    BriefVersion,
    RunId,
    SimulationDisclaimer,
)


def test_disclaimer_fields_are_frozen() -> None:
    assert field_names(SimulationDisclaimer) == ["text", "model_reference", "prompt_version"]


def test_the_frozen_text_states_the_probabilistic_nature() -> None:
    assert "probabilistic" in DEFAULT_DISCLAIMER_TEXT.lower()
    assert "corpus" in DEFAULT_DISCLAIMER_TEXT.lower()


def test_a_disclaimer_carries_the_generation_reference() -> None:
    disclaimer = SimulationDisclaimer(
        text=DEFAULT_DISCLAIMER_TEXT,
        model_reference="openai/gpt-5.1",
        prompt_version="brief.v3",
    )
    assert disclaimer.model_reference == "openai/gpt-5.1"
    assert disclaimer.prompt_version == "brief.v3"


def test_the_aggregate_disclaimer_is_optional_only_until_publication() -> None:
    assert "disclaimer" in field_names(DecisionBrief)


def test_missing_disclaimer_is_a_named_disclosure_failure() -> None:
    error = DisclosureMissing("brf_01J", "simulation_disclaimer")
    assert error.code == "DISCLOSURE_MISSING"
    assert error.missing == "simulation_disclaimer"


def test_a_draft_brief_has_no_disclaimer_yet() -> None:
    brief = DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections={},
    )
    assert brief.disclaimer is None
