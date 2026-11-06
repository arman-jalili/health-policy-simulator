"""Contract freeze: ACL purity (issue #282, implements #297).

Architecture test: no upstream context, retrieval, vector or framework type appears in
``domain/``. The domain only knows its own values plus the shared kernel.
"""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    SRC,
    domain_python_files,
    field_names,
    imported_modules,
)

from negotiation_session.domain.values import ClaimEvidence, ProvenanceRef

FORBIDDEN_PREFIXES = (
    "evidence_retrieval",
    "evidence_corpus",
    "claim_validation",
    "stakeholder_model",
    "governance_compliance",
    "simulation_orchestration",
    "sqlalchemy",
    "asyncpg",
    "fastapi",
    "pgvector",
    "numpy",
)


def test_domain_imports_nothing_from_upstream_or_frameworks() -> None:
    violations: list[str] = []
    for path in domain_python_files():
        relative = path.relative_to(SRC).as_posix()
        for module in imported_modules(relative):
            if module.startswith(FORBIDDEN_PREFIXES):
                violations.append(f"{relative}: {module}")
    assert violations == []


def test_domain_vocabulary_has_no_vectors_or_scores() -> None:
    forbidden_fields = {"vector", "embedding", "score", "cosine", "session"}
    for contract in (ClaimEvidence, ProvenanceRef):
        assert forbidden_fields.isdisjoint(field_names(contract)), contract.__name__
    for path in domain_python_files():
        relative = path.relative_to(SRC).as_posix()
        for module in imported_modules(relative):
            assert not module.startswith(("numpy", "pgvector", "sqlalchemy")), relative


def test_evidence_is_a_reference_not_a_retrieval_hit() -> None:
    assert field_names(ClaimEvidence) == ["evidence_id", "passage_id", "stance", "provenance"]
    assert field_names(ProvenanceRef) == ["source_id", "source_uri", "outlet", "published_on"]
