"""Contract freeze: service classification and layer placement (ADR-008)."""

from __future__ import annotations

import inspect
from datetime import date

import pytest

from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Offsets, SpeakerKind
from evidence_retrieval import evaluation
from evidence_retrieval.application import ports as app_ports
from evidence_retrieval.application import services
from evidence_retrieval.domain import services as domain_services
from evidence_retrieval.domain.values import ClaimText, StanceLabel


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


def _passage(passage_id: str) -> PassageView:
    return PassageView(
        passage_id=passage_id,
        article_id="art_1",
        document_id="doc_1",
        text=f"text {passage_id}",
        provenance=ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, 4),
            source_uri="s3://corpus/source.pdf",
        ),
        speaker_kind=SpeakerKind.INSTITUTION,
        citable=True,
    )


class _FakeStanceModel:
    def __init__(self, label: object) -> None:
        self.label = label

    async def classify(self, claim: str, passage: PassageView) -> StanceLabel:
        return self.label  # type: ignore[return-value]


def test_rrf_fuses_rankings_and_breaks_ties_by_first_appearance() -> None:
    a, b, c, d = (_passage(name) for name in ("a", "b", "c", "d"))

    fused = domain_services.ReciprocalRankFusion().fuse([[a, b, c], [b, a, d]])

    assert [passage.passage_id for passage in fused] == ["a", "b", "c", "d"]


def test_rrf_does_not_duplicate_a_passage_present_in_both_rankings() -> None:
    a, b = _passage("a"), _passage("b")

    fused = domain_services.ReciprocalRankFusion().fuse([[a, b], [a, b]])

    assert [passage.passage_id for passage in fused] == ["a", "b"]


async def test_stance_classifier_accepts_a_declared_label() -> None:
    classifier = domain_services.StanceClassifier(_FakeStanceModel(StanceLabel.CONTRADICTING))

    label = await classifier.classify(ClaimText("Kassenstellen"), _passage("a"))

    assert label is StanceLabel.CONTRADICTING


async def test_stance_classifier_refuses_a_label_outside_the_contract() -> None:
    classifier = domain_services.StanceClassifier(_FakeStanceModel("positive"))

    with pytest.raises(ValueError, match="unknown label"):
        await classifier.classify(ClaimText("Kassenstellen"), _passage("a"))
