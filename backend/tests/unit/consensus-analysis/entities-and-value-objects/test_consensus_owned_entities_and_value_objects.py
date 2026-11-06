"""Contract freeze: owned entities and value objects (issue #305, implements #307)."""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest
from tests.unit.consensus_analysis_contract_helpers import (
    enum_values,
    field_names,
    parameter_names,
)

from consensus_analysis.domain.entities import (
    ImpactAssessment,
    MajorityPosition,
    MinorityPosition,
    PackageComponent,
    RejectedProposal,
)
from consensus_analysis.domain.values import (
    AgendaItem,
    BaselineRef,
    BasisKind,
    ComparisonDimension,
    ConsensusOutcome,
    ConsensusOutcomeKind,
    ConsensusThreshold,
    DerivationInput,
    DerivationInputKind,
    DocumentedExample,
    EstimateBasis,
    EstimatedFigure,
    EstimateLimitation,
    FeasibilityLevel,
    FeasibilityRating,
    Horizon,
    PackageState,
    ProposalClass,
    ResolvedConflict,
    ScenarioAssumption,
    Stance,
    StanceSnapshot,
    SupportLevel,
    TopicRef,
    UncertaintyLabel,
    UnresolvedConflict,
    VetoBlockedOutcome,
)


def test_entity_fields_are_frozen() -> None:
    assert field_names(MajorityPosition) == ["proposal", "supporters", "support"]
    assert field_names(MinorityPosition) == ["holders", "objections", "proposal"]
    assert field_names(PackageComponent) == [
        "id",
        "measure",
        "accepted_by",
        "summary",
        "cost_eur",
        "requires",
    ]
    assert field_names(RejectedProposal) == ["id", "measure", "support", "reason", "holders"]
    assert field_names(ImpactAssessment) == [
        "id",
        "scenario_id",
        "package_id",
        "basis",
        "figures",
        "limitation",
        "feasibility",
    ]


def test_value_object_fields_are_frozen() -> None:
    assert field_names(ConsensusThreshold) == ["required_share", "label"]
    assert field_names(StanceSnapshot) == [
        "stakeholder",
        "stance",
        "topic",
        "weight",
        "recorded",
        "log_position",
    ]
    assert field_names(SupportLevel) == ["value", "total_weight"]
    assert field_names(VetoBlockedOutcome) == ["proposal_class", "holders"]
    assert field_names(UnresolvedConflict) == ["topic", "positions"]
    assert field_names(ResolvedConflict) == ["topic", "resolution", "holders"]
    assert field_names(ConsensusOutcome) == ["kind", "support", "veto", "minorities"]
    assert field_names(AgendaItem) == ["topic", "proposal_class"]
    assert field_names(DerivationInput) == ["kind", "reference_id", "description"]
    assert field_names(EstimateLimitation) == ["statement", "ignored_factors"]
    assert field_names(EstimateBasis) == ["kind", "inputs"]
    assert field_names(EstimatedFigure) == ["field", "value", "basis", "label", "limitation"]
    assert field_names(DocumentedExample) == ["value", "source", "description"]
    assert field_names(FeasibilityRating) == [
        "political",
        "legal",
        "administrative",
        "basis",
        "blockers",
    ]
    assert field_names(BaselineRef) == ["label", "reference"]
    assert field_names(Horizon) == ["years", "description"]
    assert field_names(ScenarioAssumption) == ["statement", "basis"]


def test_vocabulary_is_closed() -> None:
    assert enum_values(Stance) == {
        "support",
        "oppose",
        "qualify",
        "conditional_accept",
        "abstain",
    }
    assert enum_values(ConsensusOutcomeKind) == {
        "consensus",
        "partial",
        "veto_blocked",
        "unresolved",
    }
    assert enum_values(BasisKind) == {
        "measured",
        "derived",
        "modelled",
        "assumed",
        "not_estimated",
    }
    assert enum_values(UncertaintyLabel) == {"evidenced", "modelled", "assumed"}
    assert enum_values(DerivationInputKind) == {"reference_figure", "passage", "tally"}
    assert enum_values(FeasibilityLevel) == {"low", "medium", "high", "unknown"}
    assert enum_values(ComparisonDimension) == {"cost", "acceptance", "feasibility"}
    assert enum_values(PackageState) == {"draft", "composed", "assessed", "published", "abandoned"}


def test_the_blockable_proposal_vocabulary_matches_the_published_partner_list() -> None:
    from stakeholder_model.domain.values import ProposalClass as PublishedProposalClass

    assert enum_values(ProposalClass) == enum_values(PublishedProposalClass)


def test_value_objects_are_immutable_by_value() -> None:
    for frozen in (
        ConsensusThreshold,
        StanceSnapshot,
        SupportLevel,
        VetoBlockedOutcome,
        UnresolvedConflict,
        DerivationInput,
        EstimateBasis,
        EstimatedFigure,
        FeasibilityRating,
    ):
        params = getattr(frozen, "__dataclass_params__", None)
        assert params is not None, frozen.__name__
        assert params.frozen is True, frozen.__name__
        assert dataclasses.is_dataclass(frozen)


def test_stance_snapshot_classifies_approval_and_dissent() -> None:
    from consensus_analysis.domain.values import LogPosition, StakeholderId

    support = StanceSnapshot(
        stakeholder=StakeholderId("stk_1"),
        stance=Stance.SUPPORT,
        topic=TopicRef("waiting_times"),
        log_position=LogPosition(0),
    )
    oppose = StanceSnapshot(
        stakeholder=StakeholderId("stk_2"),
        stance=Stance.OPPOSE,
        topic=TopicRef("waiting_times"),
        log_position=LogPosition(1),
    )
    abstain = StanceSnapshot(
        stakeholder=StakeholderId("stk_3"),
        stance=Stance.ABSTAIN,
        topic=TopicRef("waiting_times"),
        log_position=LogPosition(2),
    )
    assert support.supports is True
    assert oppose.disapproves is True
    assert abstain.supports is False
    assert abstain.disapproves is False


def test_value_invariants_are_enforced_at_construction() -> None:
    with pytest.raises(ValueError, match="required_share"):
        ConsensusThreshold(required_share=0.0)
    with pytest.raises(ValueError, match=r"SupportLevel\.value"):
        SupportLevel(value=1.5)
    with pytest.raises(ValueError, match=r"VetoBlockedOutcome\.holders"):
        VetoBlockedOutcome(proposal_class=ProposalClass.BUDGET_FRAME, holders=())
    with pytest.raises(ValueError, match=r"Horizon\.years"):
        Horizon(years=0)
    with pytest.raises(ValueError, match=r"DerivationInput\.reference_id"):
        DerivationInput(kind=DerivationInputKind.TALLY, reference_id=" ")


def test_figure_carries_its_basis_and_label_by_construction() -> None:
    figure = EstimatedFigure(
        field="waiting_times_p50_days",
        value=Decimal("22"),
        basis=EstimateBasis(kind=BasisKind.ASSUMED),
        label=UncertaintyLabel.ASSUMED,
        limitation=EstimateLimitation(statement="assumed from a documentation example"),
    )
    assert figure.label is UncertaintyLabel.ASSUMED
    assert figure.basis.kind is BasisKind.ASSUMED


def test_entity_factories_are_frozen() -> None:
    assert parameter_names(MajorityPosition.carry) == ["proposal", "supporters", "support"]
    assert parameter_names(MinorityPosition.record) == ["holders", "objections", "proposal"]
    assert parameter_names(ImpactAssessment.assess) == [
        "scenario_id",
        "package_id",
        "figures",
        "assessment_id",
        "limitation",
        "feasibility",
    ]
