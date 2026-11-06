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
    with pytest.raises(NotImplementedError, match="#310"):
        ConsensusOutcome.partial(SupportLevel(value=0.4), ())
    with pytest.raises(NotImplementedError, match="#310"):
        ConsensusOutcome.unresolved(SupportLevel(value=0.4))
    with pytest.raises(NotImplementedError, match="#310"):
        ConsensusOutcome.consensus(SupportLevel(value=0.9))


def test_below_threshold_evaluation_is_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError, match="#310"):
        ThresholdMet().is_satisfied_by(support_value=0.4, threshold=ConsensusThreshold(0.5))


def test_threshold_rejects_a_degenerate_mandate() -> None:
    with pytest.raises(ValueError, match="required_share"):
        ConsensusThreshold(1.5)
