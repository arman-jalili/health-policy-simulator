"""Contract freeze: immutability of published briefs (issue #331, implements #344).

A published version is read-only; a change requires a new version (invariant 3).
"""

from __future__ import annotations

from tests.unit.decision_brief_contract_helpers import method_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.errors import PublishedBriefIsImmutable
from decision_brief.domain.values import BriefStatus


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
