"""Contract freeze: eight sections (issue #331, implements #339).

The publication gate contract: exactly eight mandated kinds, and a brief missing one names it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import parameter_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import IncompleteBrief
from decision_brief.domain.values import (
    REQUIRED_SECTIONS,
    SECTION_ORDINAL,
    BriefId,
    BriefVersion,
    RunId,
    SectionKind,
)


def test_the_required_set_is_the_eight_ordinals() -> None:
    assert set(SECTION_ORDINAL) == REQUIRED_SECTIONS
    assert sorted(SECTION_ORDINAL.values()) == [1, 2, 3, 4, 5, 6, 7, 8]


def test_incomplete_brief_names_the_missing_kind_and_carries_its_code() -> None:
    error = IncompleteBrief([SectionKind.IMPACT])
    assert error.code == "INCOMPLETE_BRIEF"
    assert error.status_code == 422
    assert error.missing == ("impact",)
    assert "impact" in error.message


def test_incomplete_brief_accepts_several_missing_kinds() -> None:
    error = IncompleteBrief([SectionKind.IMPACT, SectionKind.ACTORS])
    assert error.missing == ("impact", "actors_involved")


def test_publish_is_the_frozen_gate_entry_point() -> None:
    assert parameter_names(DecisionBrief.publish) == ["self"]
    version = BriefVersion(
        number=1,
        run_id=RunId("run_01J"),
        snapshot_ref="snap_01J",
        generated_at=datetime(2026, 11, 6, tzinfo=UTC),
    )
    brief = DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=version,
        sections={},
    )
    with pytest.raises(IncompleteBrief) as raised:
        brief.publish()
    assert raised.value.missing[0] == "question_summary"


def test_a_section_records_kind_and_ordinal() -> None:
    section = BriefSection(kind=SectionKind.IMPACT, ordinal=SECTION_ORDINAL[SectionKind.IMPACT])
    assert section.ordinal == 8
    assert section.statements == ()
