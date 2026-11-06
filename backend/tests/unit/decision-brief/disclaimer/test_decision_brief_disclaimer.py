"""Contract freeze: simulation disclaimer (issue #331, implements #342).

A brief without the disclaimer cannot publish; the frozen text is a constant, not a free field.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import field_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import DisclosureMissing
from decision_brief.domain.events import (
    BriefBlockedByMissingDisclosure,
    DecisionBriefPublished,
)
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    SECTION_ORDINAL,
    BriefId,
    BriefVersion,
    CitedStatement,
    EvidenceStatus,
    RunId,
    SectionKind,
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


# ── The disclosure wording is fixed, only the generation reference varies (#338) ────


def _sections() -> dict[SectionKind, BriefSection]:
    statement = CitedStatement(text="Waiting times rose.", status=EvidenceStatus.NARRATIVE)
    return {
        kind: BriefSection(
            kind=kind,
            ordinal=SECTION_ORDINAL[kind],
            statements=(statement,) if kind is SectionKind.QUESTION else (),
        )
        for kind in SectionKind
    }


def _draft(disclaimer: SimulationDisclaimer | None) -> DecisionBrief:
    return DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections=_sections(),
        disclaimer=disclaimer,
    )


def test_the_canonical_disclaimer_uses_the_frozen_wording() -> None:
    disclaimer = SimulationDisclaimer.canonical(
        model_reference="openai/gpt-5.1", prompt_version="brief.v3"
    )

    assert disclaimer.text == DEFAULT_DISCLAIMER_TEXT
    assert disclaimer.model_reference == "openai/gpt-5.1"
    assert disclaimer.prompt_version == "brief.v3"


def test_a_canonical_disclaimer_still_requires_the_generation_reference() -> None:
    with pytest.raises(ValueError, match="name the model"):
        SimulationDisclaimer.canonical(model_reference=" ", prompt_version="brief.v3")


def test_a_brief_with_the_canonical_disclaimer_publishes() -> None:
    brief = _draft(
        SimulationDisclaimer.canonical(model_reference="openai/gpt-5.1", prompt_version="brief.v3")
    )

    brief.publish()

    assert brief.is_published() is True
    assert isinstance(brief.events[-1], DecisionBriefPublished)


def test_a_brief_without_a_disclaimer_never_reaches_published() -> None:
    brief = _draft(None)

    with pytest.raises(DisclosureMissing) as raised:
        brief.publish()

    assert raised.value.missing == "simulation_disclaimer"
    assert brief.events == [
        BriefBlockedByMissingDisclosure(BriefId("brf_01J"), ("simulation_disclaimer",))
    ]
    assert brief.is_published() is False
    brief.assert_immutable()  # a blocked draft is not frozen; only a published version is
