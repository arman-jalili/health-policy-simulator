"""Contract freeze: rejected-proposal disclosure (issue #331, implements #341).

A rejected proposal is a first-class disclosed record, not an omission.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import field_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.errors import DisclosureMissing
from decision_brief.domain.events import DecisionBriefPublished, RejectedProposalDisclosed
from decision_brief.domain.projections import (
    CompromiseRecord,
    ConsensusProjection,
    RunProjection,
)
from decision_brief.domain.services import SectionAssembler
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


# ── The disclosure is in the artefact and in the audit trail (#337) ─────────────────


REJECTION = RejectedProposalRecord(
    measure="Single payer fund",
    blocking_stakeholders=("Ärztekammer",),
    reasons=("no constitutional basis",),
)

RUN = RunProjection(
    run_id=RunId("run_01J"),
    question="How should waiting times be reduced?",
    compromises=(CompromiseRecord(measure="mixed fund"),),
    rejected_proposals=(REJECTION,),
)
CONSENSUS = ConsensusProjection(run_id=RunId("run_01J"))
DISCLAIMER = SimulationDisclaimer(
    text=DEFAULT_DISCLAIMER_TEXT,
    model_reference="openai/gpt-5.1",
    prompt_version="brief.v3",
)


def test_the_assembler_discloses_rejections_inside_the_compromise_section() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    texts = [statement.text for statement in sections[SectionKind.COMPROMISES].statements]
    assert any("mixed fund" in text for text in texts)
    assert any(
        "Single payer fund" in text and "rejected" in text and "Ärztekammer" in text
        for text in texts
    )


def test_the_assembler_carries_the_run_rejections_onto_the_brief() -> None:
    assert SectionAssembler().rejected_proposals(RUN) == (REJECTION,)


def _brief_with(disclosed: tuple[RejectedProposalRecord, ...]) -> DecisionBrief:
    statement = CitedStatement(text="Waiting times rose.", status=EvidenceStatus.NARRATIVE)
    sections = {
        kind: BriefSection(
            kind=kind,
            ordinal=SECTION_ORDINAL[kind],
            statements=(statement,) if kind is SectionKind.QUESTION else (),
        )
        for kind in SectionKind
    }
    return DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections=sections,
        rejected_proposals=disclosed,
        disclaimer=DISCLAIMER,
    )


def test_a_brief_that_discloses_the_run_rejection_publishes_and_reports_it() -> None:
    brief = _brief_with((REJECTION,))

    brief.assert_rejected_proposals_disclosed(["Single payer fund"])
    brief.publish()

    assert brief.events[0] == RejectedProposalDisclosed(
        BriefId("brf_01J"), "Single payer fund", ("Ärztekammer",)
    )
    assert isinstance(brief.events[-1], DecisionBriefPublished)


def test_every_disclosed_rejection_is_audited_before_publication_event() -> None:
    second = RejectedProposalRecord(
        measure="Private hospital subsidy",
        blocking_stakeholders=("BMSGPK",),
        reasons=("budget",),
    )
    brief = _brief_with((REJECTION, second))

    brief.publish()

    disclosed = [event for event in brief.events if isinstance(event, RejectedProposalDisclosed)]
    assert [event.measure for event in disclosed] == [
        "Single payer fund",
        "Private hospital subsidy",
    ]
    assert isinstance(brief.events[-1], DecisionBriefPublished)


def test_building_the_brief_without_the_run_rejection_is_refused() -> None:
    brief = _brief_with(())

    with pytest.raises(DisclosureMissing):
        brief.assert_rejected_proposals_disclosed(
            [record.measure for record in SectionAssembler().rejected_proposals(RUN)]
        )
