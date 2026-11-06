"""Contract freeze: rejected-proposal disclosure (issue #331, implements #341).

A rejected proposal is a first-class disclosed record, not an omission.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tests.unit.decision_brief_contract_helpers import field_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import RejectedProposalRecord
from decision_brief.domain.errors import DisclosureMissing
from decision_brief.domain.events import RejectedProposalDisclosed
from decision_brief.domain.values import BriefId, BriefVersion, RunId


def test_rejected_proposal_record_is_frozen() -> None:
    assert field_names(RejectedProposalRecord) == [
        "measure",
        "blocking_stakeholders",
        "reasons",
    ]


def test_a_record_carries_blockers_and_reasons() -> None:
    record = RejectedProposalRecord(
        measure="Single payer fund",
        blocking_stakeholders=("Ärztekammer",),
        reasons=("no constitutional basis",),
    )
    assert record.blocking_stakeholders == ("Ärztekammer",)
    assert record.reasons == ("no constitutional basis",)


def test_the_aggregate_holds_the_disclosed_records() -> None:
    assert "rejected_proposals" in field_names(DecisionBrief)


def test_disclosure_missing_names_the_omitted_component() -> None:
    error = DisclosureMissing("brf_01J", "rejected_proposals")
    assert error.code == "DISCLOSURE_MISSING"
    assert error.status_code == 422
    assert error.missing == "rejected_proposals"


def test_the_disclosure_event_payload_is_frozen() -> None:
    assert field_names(RejectedProposalDisclosed) == [
        "brief_id",
        "measure",
        "blocker_ids",
    ]
    assert RejectedProposalDisclosed.name == "RejectedProposalDisclosed"


def test_a_draft_brief_starts_with_no_records() -> None:
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
    assert brief.rejected_proposals == ()
