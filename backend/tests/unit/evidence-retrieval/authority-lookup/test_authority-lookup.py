"""Contract freeze: authority is looked up from the corpus rubric, never stored here."""

from __future__ import annotations

import pytest
from tests.unit.evidence_retrieval_contract_helpers import (
    SRC,
    method_names,
    parameter_names,
)

from evidence_corpus.domain.values import AuthorityTier, ClaimType, SourceType, authority_rule
from evidence_retrieval.application.ports import QueryRewritePort
from evidence_retrieval.domain.repositories import PassageSearchPort
from evidence_retrieval.domain.values import AuthorityWeight


def test_corpus_port_exposes_the_authority_rule_lookup() -> None:
    assert "search" in method_names(PassageSearchPort)
    assert "authority_rule" in method_names(PassageSearchPort)
    assert parameter_names(PassageSearchPort.authority_rule) == ["self", "claim_type"]


def test_authority_weight_is_numeric_and_tier_relative() -> None:
    weight = AuthorityWeight(tier=AuthorityTier.PRESS_REPORT, weight=0.3)

    assert weight.tier is AuthorityTier.PRESS_REPORT
    assert 0.0 <= weight.weight <= 1.0


def test_retrieval_does_not_store_its_own_rubric() -> None:
    import ast

    forbidden: list[str] = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "evidence_corpus.domain.values":
                names = {alias.name for alias in node.names}
                if "AUTHORITY_RULES" in names or "authority_rule" in names:
                    forbidden.append(str(path))
            if isinstance(node, ast.Name) and node.id == "AUTHORITY_RULES":
                forbidden.append(str(path))

    assert forbidden == []


def test_claim_type_is_the_corpus_published_vocabulary() -> None:
    assert ClaimType.QUANTITATIVE.value == "quantitative"
    assert hasattr(QueryRewritePort, "rewrite")


def test_weight_is_derived_from_the_corpus_rule_for_the_claim_type() -> None:
    legal = authority_rule(ClaimType.LEGAL)
    quantitative = authority_rule(ClaimType.QUANTITATIVE)

    legal_legislation = AuthorityWeight.from_rule(legal, AuthorityTier.LEGISLATION)
    legal_press = AuthorityWeight.from_rule(legal, AuthorityTier.PRESS_REPORT)
    quantitative_statistics = AuthorityWeight.from_rule(
        quantitative, AuthorityTier.OFFICIAL_STATISTICS
    )

    assert legal_legislation.weight == 1.0
    assert legal_press.weight < legal_legislation.weight
    assert quantitative_statistics.weight == 1.0
    assert legal_legislation.tier is AuthorityTier.LEGISLATION


def test_weight_refuses_a_tier_outside_the_corpus_rule() -> None:
    from evidence_corpus.domain.values import AuthorityRule

    narrow = AuthorityRule(
        claim_type=ClaimType.LEGAL,
        ordered_source_types=(SourceType.LEGISLATION,),
    )

    with pytest.raises(ValueError, match="not in the corpus rule"):
        AuthorityWeight.from_rule(narrow, AuthorityTier.PRESS_REPORT)


def test_scoring_path_has_no_hardcoded_other_tier() -> None:
    source = (SRC / "application/services.py").read_text(encoding="utf-8")

    assert "AuthorityTier.OTHER" not in source
    assert "authority=authority" in source
