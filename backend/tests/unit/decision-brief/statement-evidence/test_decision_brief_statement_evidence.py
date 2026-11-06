"""Contract freeze: statement evidence (issue #331, implements #343).

An ``evidenced`` statement must cite a passage; narrative and unsupported statements say so.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import StatementWithoutCitation
from decision_brief.domain.values import (
    SECTION_ORDINAL,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitedStatement,
    EvidenceStatus,
    RunId,
    SectionKind,
)


def test_cited_statement_fields_are_frozen() -> None:
    assert field_names(CitedStatement) == ["text", "status", "citations", "claim_ids"]


def test_the_three_evidence_states_are_the_only_states() -> None:
    assert {member.value for member in EvidenceStatus} == {
        "evidenced",
        "narrative",
        "unsupported",
    }


def test_statement_without_citation_names_the_evidenced_text() -> None:
    error = StatementWithoutCitation("Waiting times rose by 12%.")
    assert error.code == "STATEMENT_WITHOUT_CITATION"
    assert error.status_code == 422
    assert error.text == "Waiting times rose by 12%."


def test_the_aggregate_owns_the_evidence_assertion() -> None:
    assert parameter_names(DecisionBrief.assert_statement_evidence) == ["self", "statement"]


def test_an_evidenced_statement_defaults_to_no_citations() -> None:
    statement = CitedStatement(text="Beds fell by 3%.", status=EvidenceStatus.EVIDENCED)
    assert statement.citations == ()
    assert statement.claim_ids == ()


# ── The evidence rule lives on the statement and is enforced in every section (#339) ──


def test_a_statement_knows_whether_it_claims_evidence() -> None:
    assert CitedStatement(text="a", status=EvidenceStatus.EVIDENCED).is_evidenced is True
    assert CitedStatement(text="b", status=EvidenceStatus.NARRATIVE).is_evidenced is False
    assert CitedStatement(text="c", status=EvidenceStatus.UNSUPPORTED).is_evidenced is False


def test_an_evidenced_statement_refuses_itself_without_a_citation() -> None:
    statement = CitedStatement(text="Waiting times rose by 12%.", status=EvidenceStatus.EVIDENCED)

    with pytest.raises(StatementWithoutCitation) as raised:
        statement.assert_evidence()

    assert raised.value.text == "Waiting times rose by 12%."


def test_narrative_and_unsupported_statements_need_no_citation() -> None:
    CitedStatement(text="The mood was tense.", status=EvidenceStatus.NARRATIVE).assert_evidence()
    CitedStatement(
        text="No citable passage exists.", status=EvidenceStatus.UNSUPPORTED
    ).assert_evidence()


def test_claim_ids_never_substitute_for_a_citation() -> None:
    statement = CitedStatement(
        text="Waiting times rose by 12%.",
        status=EvidenceStatus.EVIDENCED,
        claim_ids=("clm_01J",),
    )

    with pytest.raises(StatementWithoutCitation):
        statement.assert_evidence()


def _brief_with_statement(kind: SectionKind, statement: CitedStatement) -> DecisionBrief:
    sections = {
        section_kind: BriefSection(
            kind=section_kind,
            ordinal=SECTION_ORDINAL[section_kind],
            statements=(statement,) if section_kind is kind else (),
        )
        for section_kind in SectionKind
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


@pytest.mark.parametrize("kind", list(SectionKind))
def test_publication_checks_the_evidence_rule_in_every_section(kind: SectionKind) -> None:
    brief = _brief_with_statement(
        kind,
        CitedStatement(text="Uncited claim.", status=EvidenceStatus.EVIDENCED),
    )

    with pytest.raises(StatementWithoutCitation):
        brief.publish()

    assert brief.status is BriefStatus.BLOCKED
    assert brief.is_published() is False


def test_the_aggregate_delegates_the_rule_to_the_statement() -> None:
    brief = _brief_with_statement(
        SectionKind.QUESTION,
        CitedStatement(text="Uncited claim.", status=EvidenceStatus.EVIDENCED),
    )

    with pytest.raises(StatementWithoutCitation):
        brief.assert_statement_evidence(brief.sections[SectionKind.QUESTION].statements[0])
