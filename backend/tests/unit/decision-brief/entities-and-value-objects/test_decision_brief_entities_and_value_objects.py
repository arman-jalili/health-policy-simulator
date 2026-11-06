"""Contract freeze: entities and value objects (issue #331, implements #337).

Every concept of the module's entity table must exist with the frozen fields; the eight section
kinds must carry the frozen ordinals.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import enum_values, field_names

from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    REQUIRED_SECTIONS,
    SECTION_ORDINAL,
    ActorSummary,
    BriefComponentSlot,
    BriefStatus,
    BriefVersion,
    CitationProvenance,
    CitationReference,
    CitedStatement,
    EvidenceStatus,
    OutcomeKind,
    PassageId,
    PositionStance,
    PositionTimeline,
    RunId,
    SectionKind,
    SimulationDisclaimer,
    TopicOutcome,
)


def test_eight_section_kinds_with_frozen_wire_names() -> None:
    assert enum_values(SectionKind) == {
        "question_summary",
        "actors_involved",
        "negotiation_history",
        "conflict_analysis",
        "compromise_proposals",
        "consensus_analysis",
        "open_disputes",
        "impact",
    }
    assert len(REQUIRED_SECTIONS) == 8
    assert frozenset(SectionKind) == REQUIRED_SECTIONS


def test_section_ordinals_are_one_to_eight_in_reading_order() -> None:
    assert dict(SECTION_ORDINAL) == {
        SectionKind.QUESTION: 1,
        SectionKind.ACTORS: 2,
        SectionKind.HISTORY: 3,
        SectionKind.CONFLICTS: 4,
        SectionKind.COMPROMISES: 5,
        SectionKind.CONSENSUS: 6,
        SectionKind.OPEN_DISPUTES: 7,
        SectionKind.IMPACT: 8,
    }


def test_evidence_status_and_lifecycle_vocabularies() -> None:
    assert enum_values(EvidenceStatus) == {"evidenced", "narrative", "unsupported"}
    assert enum_values(BriefStatus) == {
        "draft",
        "validating",
        "blocked",
        "published",
        "superseded",
    }
    assert enum_values(OutcomeKind) == {"recommendation", "blocked", "open_dispute"}


def test_entity_fields_are_frozen() -> None:
    assert field_names(BriefSection) == ["kind", "ordinal", "statements"]
    assert field_names(RejectedProposalRecord) == [
        "measure",
        "blocking_stakeholders",
        "reasons",
    ]


def test_value_object_fields_are_frozen() -> None:
    assert field_names(CitedStatement) == ["text", "status", "citations", "claim_ids"]
    assert field_names(CitationReference) == ["passage_id", "provenance", "quote"]
    assert field_names(CitationProvenance) == [
        "outlet",
        "published_on",
        "medium",
        "page_from",
        "page_to",
        "source_uri",
    ]
    assert field_names(BriefVersion) == [
        "number",
        "run_id",
        "snapshot_ref",
        "generated_at",
        "previous_version",
        "reason",
    ]
    assert field_names(SimulationDisclaimer) == ["text", "model_reference", "prompt_version"]
    assert field_names(ActorSummary) == [
        "institution",
        "goals",
        "constraints",
        "adopted_positions",
    ]
    assert field_names(PositionStance) == ["round_no", "stance", "rationale"]
    assert field_names(PositionTimeline) == ["actor", "stances"]
    assert field_names(BriefComponentSlot) == ["kind", "ordinal", "completed"]
    assert field_names(TopicOutcome) == [
        "topic",
        "kind",
        "blocking_stakeholders",
        "reason",
    ]


def test_content_equality_is_value_based() -> None:
    first = CitedStatement(text="12% rise", status=EvidenceStatus.NARRATIVE)
    second = CitedStatement(text="12% rise", status=EvidenceStatus.NARRATIVE)
    assert first == second
    assert first != CitedStatement(text="12% fall", status=EvidenceStatus.NARRATIVE)


# ── Construction invariants: a value that exists is valid (#333) ───────────────────

VALID_PROVENANCE = CitationProvenance(
    outlet="Der Standard",
    published_on=date(2026, 1, 2),
    medium="print",
    page_from=1,
    page_to=2,
    source_uri="https://example.test/a",
)


def test_a_section_cannot_sit_at_the_wrong_ordinal() -> None:
    with pytest.raises(ValueError, match="belongs at ordinal 8"):
        BriefSection(kind=SectionKind.IMPACT, ordinal=3)


def test_a_statement_requires_text() -> None:
    with pytest.raises(ValueError, match="requires text"):
        CitedStatement(text="   ", status=EvidenceStatus.NARRATIVE)


def test_a_citation_requires_a_passage_id() -> None:
    with pytest.raises(ValueError, match="requires a passage id"):
        CitationReference(passage_id=PassageId(""))


def test_a_blank_citation_quote_is_rejected() -> None:
    with pytest.raises(ValueError, match="quote must not be blank"):
        CitationReference(passage_id=PassageId("psg_01J"), quote=" ")


def test_provenance_pages_are_one_based_and_ordered() -> None:
    with pytest.raises(ValueError, match="1-based"):
        CitationProvenance(
            outlet="Der Standard",
            published_on=date(2026, 1, 2),
            medium="print",
            page_from=0,
            page_to=1,
            source_uri="https://example.test/a",
        )
    with pytest.raises(ValueError, match="must not precede"):
        CitationProvenance(
            outlet="Der Standard",
            published_on=date(2026, 1, 2),
            medium="print",
            page_from=4,
            page_to=2,
            source_uri="https://example.test/a",
        )


def test_provenance_requires_an_openable_source() -> None:
    with pytest.raises(ValueError, match="source URI"):
        CitationProvenance(
            outlet="Der Standard",
            published_on=date(2026, 1, 2),
            medium="print",
            page_from=1,
            page_to=1,
            source_uri=" ",
        )


def test_a_rejected_proposal_needs_a_measure_and_a_blocker() -> None:
    with pytest.raises(ValueError, match="requires the measure"):
        RejectedProposalRecord(measure=" ", blocking_stakeholders=("Ärztekammer",), reasons=())
    with pytest.raises(ValueError, match="stakeholders that blocked it"):
        RejectedProposalRecord(measure="Single payer fund", blocking_stakeholders=(), reasons=())


def test_a_disclaimer_requires_the_generation_reference() -> None:
    with pytest.raises(ValueError, match="requires text"):
        SimulationDisclaimer(text="", model_reference="m", prompt_version="p")
    with pytest.raises(ValueError, match="name the model"):
        SimulationDisclaimer(text=DEFAULT_DISCLAIMER_TEXT, model_reference=" ", prompt_version="p")
    with pytest.raises(ValueError, match="name the prompt version"):
        SimulationDisclaimer(text=DEFAULT_DISCLAIMER_TEXT, model_reference="m", prompt_version=" ")


def test_a_version_starts_at_one_and_pins_the_snapshot() -> None:
    generated = datetime(2026, 11, 6, tzinfo=UTC)
    with pytest.raises(ValueError, match="starts at 1"):
        BriefVersion(number=0, run_id=RunId("run_01J"), snapshot_ref="s", generated_at=generated)
    with pytest.raises(ValueError, match="snapshot"):
        BriefVersion(number=1, run_id=RunId("run_01J"), snapshot_ref=" ", generated_at=generated)
    with pytest.raises(ValueError, match="timezone-aware"):
        BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="s",
            generated_at=datetime(2026, 11, 6),
        )


def test_a_successor_must_reference_an_earlier_version_with_a_reason() -> None:
    generated = datetime(2026, 11, 6, tzinfo=UTC)
    with pytest.raises(ValueError, match="earlier version"):
        BriefVersion(
            number=2,
            run_id=RunId("run_01J"),
            snapshot_ref="s",
            generated_at=generated,
            previous_version=2,
            reason="fix",
        )
    with pytest.raises(ValueError, match="requires a reason"):
        BriefVersion(
            number=2,
            run_id=RunId("run_01J"),
            snapshot_ref="s",
            generated_at=generated,
            previous_version=1,
        )
    with pytest.raises(ValueError, match="only a successor"):
        BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="s",
            generated_at=generated,
            reason="not a successor",
        )


def test_actor_identity_fields_are_required() -> None:
    with pytest.raises(ValueError, match="institution"):
        ActorSummary(institution=" ")
    with pytest.raises(ValueError, match="1-based"):
        PositionStance(round_no=0, stance="pro")
    with pytest.raises(ValueError, match="requires a stance"):
        PositionStance(round_no=1, stance=" ")
    with pytest.raises(ValueError, match="requires an actor"):
        PositionTimeline(actor=" ")


def test_a_component_slot_cannot_sit_at_the_wrong_ordinal() -> None:
    with pytest.raises(ValueError, match="belongs at ordinal 1"):
        BriefComponentSlot(kind=SectionKind.QUESTION, ordinal=2)


def test_a_blocked_topic_must_name_its_blockers_and_is_never_a_recommendation() -> None:
    with pytest.raises(ValueError, match="who blocked it"):
        TopicOutcome(topic="Single payer fund", kind=OutcomeKind.BLOCKED)
    blocked = TopicOutcome(
        topic="Single payer fund",
        kind=OutcomeKind.BLOCKED,
        blocking_stakeholders=("Ärztekammer",),
    )
    assert blocked.is_recommendation is False
    recommended = TopicOutcome(topic="Waiting times", kind=OutcomeKind.RECOMMENDATION)
    assert recommended.is_recommendation is True
