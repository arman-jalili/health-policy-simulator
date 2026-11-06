"""ACL mapping from published upstream views to domain values (issue #297)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from claim_validation.interfaces.published import ClaimVerdictView
from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import Offsets
from evidence_retrieval.domain.values import StanceLabel
from evidence_retrieval.interfaces.published import (
    EvidenceCandidateView,
    EvidencePackView,
    RetrievalTraceView,
    ScoreView,
)
from negotiation_session.domain.values import EvidencePackId, StakeholderId, TopicRef
from negotiation_session.infrastructure.acl import (
    ClaimVerdictAcl,
    EvidencePackAcl,
    StakeholderProfileAcl,
)
from stakeholder_model.domain.values import (
    BudgetPeriod,
    InstitutionCategory,
    PowerSourceKind,
    ProposalClass,
)
from stakeholder_model.interfaces.published import (
    BudgetView,
    ConstraintView,
    InstitutionView,
    InterestView,
    MandateScopeView,
    PriorityView,
    StakeholderProfileView,
    VetoRightView,
)


def _provenance() -> ProvenanceView:
    return ProvenanceView(
        outlet="Der Standard",
        published_on=date(2026, 1, 1),
        medium="print",
        page_from=1,
        page_to=2,
        offsets=Offsets(0, 10),
        source_uri="https://example.test/article",
    )


def _pack() -> EvidencePackView:
    return EvidencePackView(
        pack_id="pack_1",
        claim="Costs are rising",
        snapshot_id="snap_1",
        index_version="v1",
        candidates=[
            EvidenceCandidateView(
                passage_id="psg_1",
                stance=StanceLabel.SUPPORTING,
                score=ScoreView(
                    authority=0.1,
                    lexical=0.1,
                    semantic=0.1,
                    recency=0.1,
                    directness=0.1,
                    final=0.1,
                ),
                provenance=_provenance(),
            )
        ],
        absence=None,
        trace=RetrievalTraceView(
            embedding_model="model",
            reranker_model="reranker",
            query_rewrite="rewrite",
            stance_counts={StanceLabel.SUPPORTING: 1},
            retrieval_mode="hybrid",
            index_version="v1",
        ),
        frozen_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _profile() -> StakeholderProfileView:
    return StakeholderProfileView(
        stakeholder_id="stk_a",
        identity=InstitutionView(
            name="ÖGK",
            short_name="ÖGK",
            category=InstitutionCategory.PAYER,
            code="oegk",
        ),
        interests=(InterestView(topic="costs", goal="cap spending", weight=0.5),),
        constraints=(ConstraintView(statement="no premium increase", topic="costs"),),
        budget=BudgetView(
            amount_eur=Decimal("1000"),
            period=BudgetPeriod.ANNUAL,
            tolerance=0.1,
            source_citation="budget act",
            source_kind=PowerSourceKind.STATUTORY,
            source_as_of=date(2026, 1, 1),
        ),
        mandate_scope=MandateScopeView(
            topics=("costs", "access"),
            description="mandate",
            source_citation="statute",
            source_kind=PowerSourceKind.STATUTORY,
            source_as_of=date(2026, 1, 1),
        ),
        priorities=(PriorityView(rank=1, topic="costs"),),
        red_lines=("no premium increase",),
        veto_rights=(
            VetoRightView(
                proposal_class=ProposalClass.BUDGET_FRAME,
                source_citation="statute",
                source_kind=PowerSourceKind.STATUTORY,
                source_as_of=date(2026, 1, 1),
            ),
        ),
        positions=(),
        profile_version="v1",
    )


def test_evidence_pack_maps_to_vector_free_references() -> None:
    references = EvidencePackAcl().to_claim_evidence(_pack())
    assert len(references) == 1
    reference = references[0]
    assert reference.evidence_id == EvidencePackId("pack_1")
    assert reference.passage_id == "psg_1"
    assert reference.stance == "supporting"
    assert reference.provenance is not None
    assert reference.provenance.source_id == "snap_1"
    assert reference.provenance.outlet == "Der Standard"
    assert not hasattr(reference, "score")


def test_partner_profile_maps_to_the_domain_binding() -> None:
    binding = StakeholderProfileAcl().to_binding(
        _profile(), persona_version="p1", allowed_evidence_tiers=("authoritative",)
    )
    assert binding.stakeholder_id == StakeholderId("stk_a")
    assert binding.institution_name == "ÖGK"
    assert binding.institution_code == "oegk"
    assert binding.interests == ("costs: cap spending",)
    assert binding.constraints == ("no premium increase",)
    assert binding.red_lines == ("no premium increase",)
    assert binding.veto_classes == ("budget_frame",)
    assert binding.mandate_topics == (TopicRef("costs"), TopicRef("access"))
    assert binding.profile_version == "v1"
    assert binding.persona_version == "p1"
    assert binding.allowed_evidence_tiers == ("authoritative",)


def test_only_verified_or_unsupported_claims_pass_the_gate() -> None:
    gate = ClaimVerdictAcl()

    def verdict(value: str) -> ClaimVerdictView:
        return ClaimVerdictView(
            claim_id="clm_1", verdict=value, claim_type="quantitative", sources=(), delta=None
        )

    assert gate.accepts(verdict("verified"))
    assert gate.accepts(verdict("unsupported"))
    assert not gate.accepts(verdict("contradicted"))
    assert not gate.accepts(verdict("ambiguous"))
    assert not gate.accepts(verdict("pending"))
