"""Contract freeze: veto precedence (issue #305, implements #309)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.services import ConsensusRule, NotVetoed
from consensus_analysis.domain.values import (
    ConsensusOutcome,
    ConsensusOutcomeKind,
    ProposalClass,
    StakeholderId,
    SupportLevel,
    TopicRef,
    VetoBlockedOutcome,
)
from stakeholder_model.domain.values import (
    BudgetPeriod,
    InstitutionCategory,
    PowerSourceKind,
)
from stakeholder_model.domain.values import (
    ProposalClass as PublishedProposalClass,
)
from stakeholder_model.interfaces.published import (
    BudgetView,
    InstitutionView,
    MandateScopeView,
    StakeholderProfileView,
    VetoRightView,
)


def test_veto_precedes_the_threshold_in_the_rule_declaration() -> None:
    assert field_names(ConsensusRule) == ["veto", "threshold"]
    assert isinstance(ConsensusRule().veto, NotVetoed)


def test_veto_specification_signature_is_frozen() -> None:
    assert parameter_names(NotVetoed.holders_for) == ["self", "proposal_class", "vetoes"]


def test_rule_evaluation_takes_every_voice_into_account() -> None:
    assert parameter_names(ConsensusRule.evaluate) == [
        "self",
        "proposal_class",
        "stances",
        "threshold",
        "vetoes",
    ]


def test_veto_blocked_is_a_first_class_outcome() -> None:
    assert ConsensusOutcomeKind.VETO_BLOCKED.value == "veto_blocked"
    assert "VETO_BLOCKED" in ConsensusOutcomeKind.__members__
    outcome = ConsensusOutcome.veto_blocked(
        VetoBlockedOutcome(
            proposal_class=ProposalClass.BUDGET_FRAME,
            holders=(StakeholderId("stk_bva"),),
        ),
        SupportLevel(value=0.78),
    )
    assert outcome.kind is ConsensusOutcomeKind.VETO_BLOCKED
    assert outcome.support.value == pytest.approx(0.78)


def test_the_rule_blocks_a_seven_of_nine_class_that_would_otherwise_carry() -> None:
    from consensus_analysis.domain.services import ConsensusRule
    from consensus_analysis.domain.values import (
        ConsensusThreshold,
        LogPosition,
        Stance,
        StanceSnapshot,
    )

    def snapshot(index: int, stance: Stance) -> tuple[StakeholderId, StanceSnapshot]:
        stakeholder = StakeholderId(f"stk_{index}")
        return stakeholder, StanceSnapshot(
            stakeholder=stakeholder,
            stance=stance,
            topic=TopicRef("waiting_times"),
            log_position=LogPosition(index),
        )

    stances = dict(
        [snapshot(index, Stance.SUPPORT) for index in range(7)]
        + [snapshot(7, Stance.OPPOSE), snapshot(8, Stance.OPPOSE)]
    )
    outcome = ConsensusRule().evaluate(
        proposal_class=ProposalClass.BUDGET_FRAME,
        stances=stances,
        threshold=ConsensusThreshold.from_mandate(0.6),
        vetoes={StakeholderId("stk_7"): frozenset({ProposalClass.BUDGET_FRAME})},
    )
    assert outcome.kind is ConsensusOutcomeKind.VETO_BLOCKED
    assert outcome.veto is not None
    assert outcome.veto.holders == (StakeholderId("stk_7"),)


def test_a_veto_holder_is_named_deterministically() -> None:
    vetoes = {
        StakeholderId("stk_z"): frozenset({ProposalClass.FEE_SCHEDULE}),
        StakeholderId("stk_a"): frozenset({ProposalClass.FEE_SCHEDULE}),
        StakeholderId("stk_m"): frozenset({ProposalClass.HOSPITAL_PLAN}),
    }
    assert NotVetoed().holders_for(proposal_class=ProposalClass.FEE_SCHEDULE, vetoes=vetoes) == (
        StakeholderId("stk_a"),
        StakeholderId("stk_z"),
    )


def test_veto_holders_must_be_named() -> None:
    with pytest.raises(ValueError, match="holders"):
        VetoBlockedOutcome(proposal_class=ProposalClass.FEE_SCHEDULE, holders=())


# ── issue #309: the veto map is read from the partner contract, never inferred ─────────────────


def _profile(*classes: str) -> StakeholderProfileView:
    return StakeholderProfileView(
        stakeholder_id="stk_bva",
        identity=InstitutionView(
            name="Dachverband der Sozialversicherungstraeger",
            short_name="BVA",
            category=InstitutionCategory.INSURER_ASSOCIATION,
            code="bva",
        ),
        interests=(),
        constraints=(),
        budget=BudgetView(
            amount_eur=Decimal("0"),
            period=BudgetPeriod.ANNUAL,
            tolerance=0.0,
            source_citation="paragraph 23 ASVG",
            source_kind=PowerSourceKind.STATUTORY,
            source_as_of=date(2026, 1, 1),
        ),
        mandate_scope=MandateScopeView(
            topics=("budget_frame",),
            description="cost containment",
            source_citation="paragraph 23 ASVG",
            source_kind=PowerSourceKind.STATUTORY,
            source_as_of=date(2026, 1, 1),
        ),
        priorities=(),
        red_lines=(),
        veto_rights=tuple(
            VetoRightView(
                proposal_class=PublishedProposalClass(item),
                source_citation="paragraph 23 ASVG",
                source_kind=PowerSourceKind.STATUTORY,
                source_as_of=date(2026, 1, 1),
            )
            for item in classes
        ),
        positions=(),
        profile_version="v1",
    )


def test_the_veto_map_is_read_from_the_published_profile() -> None:
    from consensus_analysis.infrastructure.acl import StakeholderPowersAcl

    classes = StakeholderPowersAcl().to_veto_classes(_profile("budget_frame", "fee_schedule"))

    assert classes == frozenset({ProposalClass.BUDGET_FRAME, ProposalClass.FEE_SCHEDULE})


def test_an_institution_without_a_veto_yields_an_empty_set_not_a_missing_entry() -> None:
    from consensus_analysis.infrastructure.acl import StakeholderPowersAcl

    assert StakeholderPowersAcl().to_veto_classes(_profile()) == frozenset()


def test_a_veto_over_unanimous_support_is_still_blocked() -> None:
    """Veto precedence is absolute: it is not a tie-breaker against dissent."""
    from consensus_analysis.domain.services import ConsensusRule
    from consensus_analysis.domain.values import (
        ConsensusThreshold,
        LogPosition,
        Stance,
        StanceSnapshot,
    )

    stances = {
        StakeholderId(f"stk_{index}"): StanceSnapshot(
            stakeholder=StakeholderId(f"stk_{index}"),
            stance=Stance.SUPPORT,
            topic=TopicRef("waiting_times"),
            log_position=LogPosition(index),
        )
        for index in range(9)
    }
    outcome = ConsensusRule().evaluate(
        proposal_class=ProposalClass.BUDGET_FRAME,
        stances=stances,
        threshold=ConsensusThreshold.from_mandate(0.5),
        vetoes={StakeholderId("stk_0"): frozenset({ProposalClass.BUDGET_FRAME})},
    )

    assert outcome.kind is ConsensusOutcomeKind.VETO_BLOCKED
    assert outcome.support.value == pytest.approx(1.0)


def test_every_veto_holder_is_named_not_just_the_first() -> None:
    from consensus_analysis.domain.services import ConsensusRule
    from consensus_analysis.domain.values import (
        ConsensusThreshold,
        LogPosition,
        Stance,
        StanceSnapshot,
    )

    stances = {
        StakeholderId("stk_a"): StanceSnapshot(
            stakeholder=StakeholderId("stk_a"),
            stance=Stance.SUPPORT,
            topic=TopicRef("waiting_times"),
            log_position=LogPosition(0),
        )
    }
    outcome = ConsensusRule().evaluate(
        proposal_class=ProposalClass.HOSPITAL_PLAN,
        stances=stances,
        threshold=ConsensusThreshold.from_mandate(0.5),
        vetoes={
            StakeholderId("stk_a"): frozenset({ProposalClass.HOSPITAL_PLAN}),
            StakeholderId("stk_b"): frozenset({ProposalClass.HOSPITAL_PLAN}),
        },
    )

    assert outcome.veto is not None
    assert outcome.veto.holders == (StakeholderId("stk_a"), StakeholderId("stk_b"))


def test_an_unrepresentable_veto_class_is_refused_not_dropped() -> None:
    from dataclasses import replace

    from consensus_analysis.domain.errors import UnknownVetoClass
    from consensus_analysis.infrastructure.acl import StakeholderPowersAcl

    profile = _profile("budget_frame")
    original = profile.veto_rights[0]
    tampered = replace(
        profile,
        veto_rights=(
            replace(original, proposal_class="chapter_unknown"),  # type: ignore[arg-type]
        ),
    )

    with pytest.raises(UnknownVetoClass):
        StakeholderPowersAcl().to_veto_classes(tampered)
