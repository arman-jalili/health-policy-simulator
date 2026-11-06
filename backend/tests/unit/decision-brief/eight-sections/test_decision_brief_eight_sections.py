"""Contract freeze and section assembly (issue #331, implements #335).

The publication gate contract: exactly eight mandated kinds, and a brief missing one names it.
The assembler contract: the eight sections are a pure, deterministic mapping from the local
projections, so regeneration reproduces the artefact (invariant 7).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import parameter_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import IncompleteBrief
from decision_brief.domain.projections import (
    ClaimVerdictProjection,
    CompromiseRecord,
    ConflictRecord,
    ConsensusProjection,
    ConsensusStatement,
    HistoryEntry,
    RunProjection,
)
from decision_brief.domain.services import SectionAssembler
from decision_brief.domain.values import (
    REQUIRED_SECTIONS,
    SECTION_ORDINAL,
    ActorSummary,
    BriefId,
    BriefVersion,
    EvidenceStatus,
    OutcomeKind,
    PassageId,
    RunId,
    SectionKind,
    TopicOutcome,
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


# ── The eight sections are assembled from the projections (#335) ────────────────────

RUN = RunProjection(
    run_id=RunId("run_01J"),
    question="How should waiting times be reduced?",
    actors=(
        ActorSummary(
            institution="BMSGPK",
            goals=("access",),
            constraints=("budget",),
            adopted_positions=("expand primary care",),
        ),
    ),
    history=(HistoryEntry(round_no=1, actor="BMSGPK", summary="opened with access", stance="pro"),),
    conflicts=(ConflictRecord(topic="funding", summary="split on the fund", holders=("BMSGPK",)),),
    compromises=(
        CompromiseRecord(measure="mixed fund", supporters=("BMSGPK",), opponents=("ÄK",)),
    ),
    claim_verdicts=(
        ClaimVerdictProjection(
            claim_id="clm_01J",
            verdict="verified",
            passage_ids=(PassageId("psg_01J"),),
        ),
        ClaimVerdictProjection(claim_id="clm_02J", verdict="unsupported"),
    ),
    blocked_topics=(
        TopicOutcome(
            topic="Single payer fund",
            kind=OutcomeKind.BLOCKED,
            blocking_stakeholders=("Ärztekammer",),
            reason="veto right",
        ),
    ),
    log_position=42,
    snapshot_ref="snap_01J",
)

CONSENSUS = ConsensusProjection(
    run_id=RunId("run_01J"),
    statements=(
        ConsensusStatement(
            topic="primary care",
            statement="expand primary care first",
            supporters=("BMSGPK",),
            minorities=("ÄK",),
        ),
    ),
    unresolved=(TopicOutcome(topic="private hospitals", kind=OutcomeKind.OPEN_DISPUTE),),
    impact=("modelled cost: illustrative only",),
    log_position=42,
)


def test_assembly_returns_all_eight_sections_in_reading_order() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    assert list(sections) == list(SectionKind)
    assert [section.ordinal for section in sections.values()] == list(range(1, 9))


def test_the_question_is_the_narrative_opening() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    (statement,) = sections[SectionKind.QUESTION].statements
    assert statement.text == "How should waiting times be reduced?"
    assert statement.status is EvidenceStatus.NARRATIVE


def test_actor_history_conflict_and_compromise_sections_are_rendered() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    assert "budget" in sections[SectionKind.ACTORS].statements[0].text
    assert "Round 1" in sections[SectionKind.HISTORY].statements[0].text
    assert "split on the fund" in sections[SectionKind.CONFLICTS].statements[0].text
    assert "mixed fund" in sections[SectionKind.COMPROMISES].statements[0].text


def test_consensus_statements_carry_majority_and_minority() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    text = sections[SectionKind.CONSENSUS].statements[0].text
    assert "expand primary care first" in text
    assert "majority: BMSGPK" in text
    assert "minority: ÄK" in text


def test_a_verdict_with_a_passage_is_evidenced_and_cites_it() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    verdicts = [s for s in sections[SectionKind.CONSENSUS].statements if s.claim_ids]
    evidenced = next(s for s in verdicts if s.claim_ids == ("clm_01J",))
    assert evidenced.status is EvidenceStatus.EVIDENCED
    assert [str(c.passage_id) for c in evidenced.citations] == ["psg_01J"]
    assert evidenced.citations[0].is_resolved() is False  # the gate resolves it, not the assembler


def test_a_verdict_without_a_passage_is_marked_unsupported_not_evidenced() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    unsupported = next(
        s for s in sections[SectionKind.CONSENSUS].statements if s.claim_ids == ("clm_02J",)
    )
    assert unsupported.status is EvidenceStatus.UNSUPPORTED
    assert "no citable passage" in unsupported.text


def test_disputes_and_blocked_topics_are_stated_in_section_seven() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    texts = [statement.text for statement in sections[SectionKind.OPEN_DISPUTES].statements]
    assert any("Single payer fund" in text and "blocked by Ärztekammer" in text for text in texts)
    assert any("private hospitals" in text for text in texts)


def test_outcomes_never_promote_a_blocked_topic_to_a_recommendation() -> None:
    outcomes = SectionAssembler().outcomes(RUN, CONSENSUS)

    blocked = next(o for o in outcomes if o.topic == "Single payer fund")
    assert blocked.kind is OutcomeKind.BLOCKED
    assert blocked.is_recommendation is False
    assert all(not o.is_recommendation for o in outcomes)


def test_assembly_is_deterministic() -> None:
    assembler = SectionAssembler()

    first = assembler.assemble(run=RUN, consensus=CONSENSUS)
    second = assembler.assemble(run=RUN, consensus=CONSENSUS)

    assert first == second
    assert first[SectionKind.CONSENSUS] == second[SectionKind.CONSENSUS]


def test_every_evidenced_statement_carries_a_citation() -> None:
    sections = SectionAssembler().assemble(run=RUN, consensus=CONSENSUS)

    for section in sections.values():
        for statement in section.statements:
            if statement.status is EvidenceStatus.EVIDENCED:
                assert statement.citations, statement.text
