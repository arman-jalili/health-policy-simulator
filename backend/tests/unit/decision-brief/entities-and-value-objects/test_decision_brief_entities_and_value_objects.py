"""Contract freeze: entities and value objects (issue #331, implements #337).

Every concept of the module's entity table must exist with the frozen fields; the eight section
kinds must carry the frozen ordinals.
"""

from __future__ import annotations

from tests.unit.decision_brief_contract_helpers import enum_values, field_names

from decision_brief.domain.entities import BriefSection, RejectedProposalRecord
from decision_brief.domain.values import (
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
    PositionStance,
    PositionTimeline,
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
