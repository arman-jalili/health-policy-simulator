"""Contract freeze: statement evidence (issue #331, implements #343).

An ``evidenced`` statement must cite a passage; narrative and unsupported statements say so.
"""

from __future__ import annotations

from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.errors import StatementWithoutCitation
from decision_brief.domain.values import CitedStatement, EvidenceStatus


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
