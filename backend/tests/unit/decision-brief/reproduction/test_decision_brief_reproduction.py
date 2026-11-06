"""Contract freeze: reproduction from the run log (issue #331, implements #346).

The brief is a projection: the log position and snapshot are part of the frozen input contract.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import BriefReproductionMismatch
from decision_brief.domain.projections import (
    ConsensusProjection,
    ReproductionInput,
    RunProjection,
)
from decision_brief.domain.services import ReproductionCheck, ReproductionChecker
from decision_brief.domain.values import (
    SECTION_ORDINAL,
    BriefId,
    BriefVersion,
    CitationProvenance,
    CitationReference,
    CitedStatement,
    EvidenceStatus,
    PassageId,
    RunId,
    SectionKind,
)


def test_run_projection_carries_the_reproduction_anchor() -> None:
    fields = field_names(RunProjection)
    assert "log_position" in fields
    assert "snapshot_ref" in fields
    assert fields[:2] == ["run_id", "question"]


def test_consensus_projection_carries_its_log_position() -> None:
    assert "log_position" in field_names(ConsensusProjection)


def test_reproduction_input_is_the_complete_allowed_read_set() -> None:
    assert field_names(ReproductionInput) == ["run", "consensus"]


def test_the_reproduction_checker_is_a_domain_contract() -> None:
    assert parameter_names(ReproductionChecker.assert_reproduces) == [
        "self",
        "published",
        "regenerated",
    ]


def test_reproduction_mismatch_names_run_and_section() -> None:
    error = BriefReproductionMismatch("run_01J", "impact")
    assert error.code == "BRIEF_REPRODUCTION_MISMATCH"
    assert error.run_id == "run_01J"
    assert error.section == "impact"


# ── Regeneration reproduces everything except narrative wording (#342) ──────────────


PROVENANCE = CitationProvenance(
    outlet="Der Standard",
    published_on=date(2026, 1, 2),
    medium="print",
    page_from=1,
    page_to=2,
    source_uri="https://example.test/a",
)


def _statement(text: str, status: EvidenceStatus, passage: str | None = None) -> CitedStatement:
    citations: tuple[CitationReference, ...] = ()
    if passage is not None:
        citations = (
            CitationReference(
                passage_id=PassageId(passage), provenance=PROVENANCE, quote="quoted span"
            ),
        )
    return CitedStatement(text=text, status=status, citations=citations, claim_ids=("clm_01J",))


def _brief(statements: tuple[CitedStatement, ...]) -> DecisionBrief:
    sections = {
        kind: BriefSection(
            kind=kind,
            ordinal=SECTION_ORDINAL[kind],
            statements=statements if kind is SectionKind.QUESTION else (),
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
    )


def test_identical_regeneration_passes() -> None:
    statements = (
        _statement("Waiting times rose by 12%.", EvidenceStatus.EVIDENCED, "psg_01J"),
        _statement("The mood was tense.", EvidenceStatus.NARRATIVE),
    )

    ReproductionCheck().assert_reproduces(_brief(statements), _brief(statements))


def test_narrative_wording_may_change_between_generations() -> None:
    published = _brief((_statement("The mood was tense.", EvidenceStatus.NARRATIVE),))
    regenerated = _brief((_statement("Tempers were short.", EvidenceStatus.NARRATIVE),))

    ReproductionCheck().assert_reproduces(published, regenerated)


def test_evidenced_text_must_not_change() -> None:
    published = _brief(
        (_statement("Waiting times rose by 12%.", EvidenceStatus.EVIDENCED, "psg_01J"),)
    )
    regenerated = _brief(
        (_statement("Waiting times rose by 40%.", EvidenceStatus.EVIDENCED, "psg_01J"),)
    )

    with pytest.raises(BriefReproductionMismatch) as raised:
        ReproductionCheck().assert_reproduces(published, regenerated)
    assert raised.value.section == "question_summary"


def test_a_changed_citation_target_breaks_reproduction() -> None:
    published = _brief(
        (_statement("Waiting times rose by 12%.", EvidenceStatus.EVIDENCED, "psg_01J"),)
    )
    regenerated = _brief(
        (_statement("Waiting times rose by 12%.", EvidenceStatus.EVIDENCED, "psg_99J"),)
    )

    with pytest.raises(BriefReproductionMismatch):
        ReproductionCheck().assert_reproduces(published, regenerated)


def test_a_changed_evidence_status_breaks_reproduction() -> None:
    published = _brief((_statement("Waiting times rose.", EvidenceStatus.NARRATIVE),))
    regenerated = _brief((_statement("Waiting times rose.", EvidenceStatus.EVIDENCED, "psg_01J"),))

    with pytest.raises(BriefReproductionMismatch):
        ReproductionCheck().assert_reproduces(published, regenerated)


def test_a_missing_section_names_the_section() -> None:
    statements = (_statement("Waiting times rose.", EvidenceStatus.NARRATIVE),)
    published = _brief(statements)
    regenerated = _brief(statements)
    regenerated.sections.pop(SectionKind.IMPACT)

    with pytest.raises(BriefReproductionMismatch) as raised:
        ReproductionCheck().assert_reproduces(published, regenerated)
    assert raised.value.section == "impact"
