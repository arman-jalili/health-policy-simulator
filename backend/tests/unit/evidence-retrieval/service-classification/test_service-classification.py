"""Contract freeze: service classification and layer placement (ADR-008)."""

from __future__ import annotations

import inspect

from evidence_retrieval import evaluation
from evidence_retrieval.application import ports as app_ports
from evidence_retrieval.application import services
from evidence_retrieval.domain import services as domain_services


def test_application_services_orchestrate_io() -> None:
    assert services.SearchEvidenceCandidates.__module__.startswith("evidence_retrieval.application")
    assert services.AssembleEvidencePack.__module__.startswith("evidence_retrieval.application")
    assert inspect.iscoroutinefunction(services.SearchEvidenceCandidates.execute)
    assert inspect.iscoroutinefunction(services.AssembleEvidencePack.execute)


def test_domain_services_are_pure_and_own_the_rules() -> None:
    for name in (
        "ScoreEvidenceCandidates",
        "ApplyRecencyPolicy",
        "ReciprocalRankFusion",
        "StanceClassifier",
    ):
        service = getattr(domain_services, name)
        assert service.__module__.startswith("evidence_retrieval.domain")

    assert not inspect.iscoroutinefunction(domain_services.ScoreEvidenceCandidates.score)
    assert not inspect.iscoroutinefunction(domain_services.ApplyRecencyPolicy.apply)
    assert not inspect.iscoroutinefunction(domain_services.ReciprocalRankFusion.fuse)
    assert inspect.iscoroutinefunction(domain_services.StanceClassifier.classify)


def test_vendor_capabilities_are_ports_not_domain_concepts() -> None:
    for name in ("EmbeddingPort", "RerankerPort", "QueryRewritePort", "RetrievalReadinessPort"):
        assert hasattr(app_ports, name)
        assert getattr(app_ports, name).__module__ == "evidence_retrieval.application.ports"


def test_evaluation_is_a_harness_not_a_domain_concept() -> None:
    assert evaluation.EvaluationHarness.__module__ == "evidence_retrieval.evaluation"
    assert not hasattr(domain_services, "EvaluationHarness")
