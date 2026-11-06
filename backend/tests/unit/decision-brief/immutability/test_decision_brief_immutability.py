"""Contract freeze: immutability of published briefs (issue #331, implements #344).

A published version is read-only; a change requires a new version (invariant 3).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import method_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import DisclosureMissing, PublishedBriefIsImmutable
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    SECTION_ORDINAL,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitedStatement,
    EvidenceStatus,
    RunId,
    SectionKind,
    SimulationDisclaimer,
)


def test_the_lifecycle_has_a_single_frozen_state() -> None:
    assert BriefStatus.PUBLISHED.value == "published"
    assert BriefStatus.SUPERSEDED.value == "superseded"


def test_published_brief_immutable_is_a_conflict() -> None:
    error = PublishedBriefIsImmutable("brf_01J")
    assert error.code == "PUBLISHED_BRIEF_IMMUTABLE"
    assert error.status_code == 409
    assert error.brief_id == "brf_01J"


def test_the_aggregate_exposes_no_in_place_mutator() -> None:
    """Publication freezes content: there is no add_section/set_* surface to call."""
    public = method_names(DecisionBrief)
    forbidden = {name for name in public if name.startswith(("add_", "set_", "update_", "append_"))}
    assert forbidden == set()


def test_the_immutability_assertion_is_frozen() -> None:
    assert "assert_immutable" in method_names(DecisionBrief)


def test_publish_is_the_only_transition_into_published() -> None:
    assert "publish" in method_names(DecisionBrief)
    assert "supersede_by" in method_names(DecisionBrief)


# ── Published means read-only, and a blocked draft can still be fixed (#340) ────────


DISCLAIMER = SimulationDisclaimer(
    text=DEFAULT_DISCLAIMER_TEXT,
    model_reference="openai/gpt-5.1",
    prompt_version="brief.v3",
)


def _draft() -> DecisionBrief:
    statement = CitedStatement(text="Waiting times rose.", status=EvidenceStatus.NARRATIVE)
    return DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections={
            kind: BriefSection(
                kind=kind,
                ordinal=SECTION_ORDINAL[kind],
                statements=(statement,) if kind is SectionKind.QUESTION else (),
            )
            for kind in SectionKind
        },
        disclaimer=DISCLAIMER,
    )


def _published() -> DecisionBrief:
    brief = _draft()
    brief.publish()
    return brief


def test_a_published_brief_rejects_attribute_changes() -> None:
    brief = _published()

    with pytest.raises(PublishedBriefIsImmutable):
        brief.status = BriefStatus.DRAFT
    with pytest.raises(PublishedBriefIsImmutable):
        brief.disclaimer = None
    with pytest.raises(PublishedBriefIsImmutable):
        brief.rejected_proposals = ()


def test_a_published_brief_rejects_section_mutations() -> None:
    brief = _published()
    impact = BriefSection(kind=SectionKind.IMPACT, ordinal=SECTION_ORDINAL[SectionKind.IMPACT])

    with pytest.raises(PublishedBriefIsImmutable):
        brief.sections[SectionKind.IMPACT] = impact
    with pytest.raises(PublishedBriefIsImmutable):
        del brief.sections[SectionKind.IMPACT]
    with pytest.raises(PublishedBriefIsImmutable):
        brief.sections.clear()
    with pytest.raises(PublishedBriefIsImmutable):
        brief.sections.pop(SectionKind.IMPACT)
    with pytest.raises(PublishedBriefIsImmutable):
        brief.sections.update({SectionKind.IMPACT: impact})
    with pytest.raises(PublishedBriefIsImmutable):
        brief.sections.setdefault(SectionKind.IMPACT, impact)


def test_the_audit_event_list_stays_appendable_after_publication() -> None:
    brief = _published()

    brief.events.append(brief.events[0])

    assert len(brief.events) == 2


def test_a_blocked_draft_can_be_fixed_and_then_published() -> None:
    brief = _draft()
    brief.disclaimer = None
    with pytest.raises(DisclosureMissing):
        brief.publish()
    assert str(brief.status) == "blocked"

    brief.disclaimer = DISCLAIMER
    brief.publish()

    assert str(brief.status) == "published"
    with pytest.raises(PublishedBriefIsImmutable):
        brief.disclaimer = None


def test_a_published_brief_keeps_its_content_readable() -> None:
    brief = _published()

    assert brief.sections[SectionKind.QUESTION].ordinal == 1
    assert len(brief.sections) == 8
    assert brief.is_published() is True
