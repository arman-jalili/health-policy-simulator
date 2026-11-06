"""Contract freeze: veto precedence (issue #305, implements #309)."""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.services import ConsensusRule, NotVetoed
from consensus_analysis.domain.values import (
    ConsensusOutcome,
    ConsensusOutcomeKind,
    ProposalClass,
    StakeholderId,
    SupportLevel,
    VetoBlockedOutcome,
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
