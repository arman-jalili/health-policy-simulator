"""Contract freeze: version lineage (issue #331, implements #345).

Version N+1 references N and states a reason; N stays retrievable unchanged.
"""

from __future__ import annotations

from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.application.commands import VersionDecisionBriefRequest
from decision_brief.application.services import VersionDecisionBrief
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.events import DecisionBriefVersioned
from decision_brief.domain.repositories import DecisionBriefRepository
from decision_brief.domain.values import BriefVersion


def test_brief_version_carries_lineage_fields() -> None:
    assert field_names(BriefVersion) == [
        "number",
        "run_id",
        "snapshot_ref",
        "generated_at",
        "previous_version",
        "reason",
    ]


def test_version_request_requires_a_reason() -> None:
    assert field_names(VersionDecisionBriefRequest) == ["brief_id", "reason", "requested_by"]


def test_versioning_event_payload_is_frozen() -> None:
    assert field_names(DecisionBriefVersioned) == ["brief_id", "previous_version", "reason"]
    assert DecisionBriefVersioned.name == "DecisionBriefVersioned"


def test_the_repository_lists_all_versions_of_a_run() -> None:
    assert parameter_names(DecisionBriefRepository.versions_for_run) == ["self", "run_id"]


def test_versioning_service_names_its_collaborators() -> None:
    service = VersionDecisionBrief(
        briefs=None,  # type: ignore[arg-type]
        events=None,  # type: ignore[arg-type]
        clock=None,  # type: ignore[arg-type]
        ids=None,  # type: ignore[arg-type]
        uow=None,  # type: ignore[arg-type]
    )
    assert len(service.collaborators()) == 5
    assert "execute" in dir(service)


def test_supersede_by_takes_the_reason_as_keyword_only() -> None:
    assert parameter_names(DecisionBrief.supersede_by) == ["self", "successor", "reason"]
