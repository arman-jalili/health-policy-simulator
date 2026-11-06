"""Contract freeze: threshold (issue #305, implements #310)."""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.services import ThresholdMet
from consensus_analysis.domain.values import (
    ConsensusOutcome,
    ConsensusOutcomeKind,
    ConsensusThreshold,
    SupportLevel,
)


def test_threshold_is_rule_parameters_not_a_quorum() -> None:
    assert field_names(ConsensusThreshold) == ["required_share", "label"]
    assert ConsensusThreshold(0.5).required_share == pytest.approx(0.5)


def test_threshold_specification_signature_is_frozen() -> None:
    assert parameter_names(ThresholdMet.is_satisfied_by) == ["self", "support_value", "threshold"]


def test_support_level_surface_is_frozen() -> None:
    assert field_names(SupportLevel) == ["value", "total_weight"]
    assert parameter_names(SupportLevel.weighted) == ["stances"]
    assert parameter_names(SupportLevel.meets) == ["self", "threshold"]


def test_partial_and_unresolved_are_admissible_outcomes() -> None:
    assert ConsensusOutcomeKind.PARTIAL.value == "partial"
    assert ConsensusOutcomeKind.UNRESOLVED.value == "unresolved"
    assert ConsensusOutcome.partial(SupportLevel(value=0.4), ()).kind is (
        ConsensusOutcomeKind.PARTIAL
    )
    assert ConsensusOutcome.unresolved(SupportLevel(value=0.4)).kind is (
        ConsensusOutcomeKind.UNRESOLVED
    )
    assert ConsensusOutcome.consensus(SupportLevel(value=0.9)).kind is (
        ConsensusOutcomeKind.CONSENSUS
    )


def test_support_at_or_above_the_mandate_threshold_is_satisfied() -> None:
    threshold = ConsensusThreshold.from_mandate(0.6)
    assert ThresholdMet().is_satisfied_by(support_value=0.6, threshold=threshold) is True
    assert ThresholdMet().is_satisfied_by(support_value=0.59, threshold=threshold) is False


def test_abstentions_leave_the_denominator_and_weigh_nothing() -> None:
    from consensus_analysis.domain.values import (
        LogPosition,
        StakeholderId,
        Stance,
        StanceSnapshot,
    )

    def snapshot(
        key: str, stance: Stance, weight: float = 1.0
    ) -> tuple[StakeholderId, StanceSnapshot]:
        stakeholder = StakeholderId(key)
        return stakeholder, StanceSnapshot(
            stakeholder=stakeholder,
            stance=stance,
            weight=weight,
            log_position=LogPosition(0),
        )

    stances = dict(
        [
            snapshot("stk_1", Stance.SUPPORT, weight=0.4),
            snapshot("stk_2", Stance.OPPOSE, weight=0.1),
            snapshot("stk_3", Stance.ABSTAIN, weight=0.9),
        ]
    )
    assert SupportLevel.weighted(stances).value == pytest.approx(0.8)
    assert SupportLevel.weighted(stances).total_weight == pytest.approx(0.5)


def test_an_empty_run_has_zero_support_and_not_full_support() -> None:
    assert SupportLevel.weighted({}).value == pytest.approx(0.0)


def test_threshold_rejects_a_degenerate_mandate() -> None:
    with pytest.raises(ValueError, match="required_share"):
        ConsensusThreshold(1.5)
