"""Contract freeze: authority is looked up from the corpus rubric, never stored here."""

from __future__ import annotations

from tests.unit.evidence_retrieval_contract_helpers import (
    SRC,
    method_names,
    parameter_names,
)

from evidence_corpus.domain.values import AuthorityTier, ClaimType
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
