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
    with pytest.raises(NotImplementedError, match="#309"):
        ConsensusOutcome.veto_blocked(
            VetoBlockedOutcome(
                proposal_class=ProposalClass.BUDGET_FRAME,
                holders=(StakeholderId("stk_bva"),),
            ),
            SupportLevel(value=0.78),
        )


def test_veto_holders_must_be_named() -> None:
    with pytest.raises(ValueError, match="holders"):
        VetoBlockedOutcome(proposal_class=ProposalClass.FEE_SCHEDULE, holders=())
