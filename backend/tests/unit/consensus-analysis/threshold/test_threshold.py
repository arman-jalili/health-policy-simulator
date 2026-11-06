"""Threshold: the mandate decides, weighted support is measured (issues #305, #310).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Collaborator reachability W8)

The threshold row of the W8 table is a call-site obligation: "fails when a default threshold is
used". It is checked here rather than trusted, and support is proved to be weighted by negotiating
power instead of counted by head.
"""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.services import ThresholdMet
from consensus_analysis.domain.values import (
    ConsensusOutcome,
    ConsensusOutcomeKind,
    ConsensusThreshold,
    LogPosition,
    StakeholderId,
    Stance,
    StanceSnapshot,
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


# ── issue #310: the threshold is the mandate's, weighted by power, never a default ─────────────


def _snapshot(
    key: str, stance: Stance, *, weight: float, position: int
) -> tuple[StakeholderId, StanceSnapshot]:
    stakeholder = StakeholderId(key)
    return stakeholder, StanceSnapshot(
        stakeholder=stakeholder,
        stance=stance,
        weight=weight,
        log_position=LogPosition(position),
    )


def test_support_is_weighted_by_negotiating_power_not_by_head_count() -> None:
    """Five of nine institutions support, but they carry only 0.30 of the weight."""
    stances = dict(
        [_snapshot(f"stk_s{i}", Stance.SUPPORT, weight=0.06, position=i) for i in range(5)]
        + [_snapshot(f"stk_o{i}", Stance.OPPOSE, weight=0.28, position=10 + i) for i in range(4)]
    )

    support = SupportLevel.weighted(stances)

    assert support.value == pytest.approx(0.3 / 1.42, abs=1e-9)
    assert support.meets(ConsensusThreshold.from_mandate(0.6)) is False


def test_the_threshold_boundary_is_inclusive() -> None:
    threshold = ConsensusThreshold.from_mandate(0.5)
    assert SupportLevel(value=0.5).meets(threshold) is True
    assert SupportLevel(value=0.4999).meets(threshold) is False


def test_a_unanimous_mandate_threshold_requires_everyone() -> None:
    stances = dict(
        [
            _snapshot("stk_1", Stance.SUPPORT, weight=0.5, position=0),
            _snapshot("stk_2", Stance.SUPPORT, weight=0.5, position=1),
            _snapshot("stk_3", Stance.ABSTAIN, weight=0.5, position=2),
        ]
    )
    assert SupportLevel.weighted(stances).meets(ConsensusThreshold.from_mandate(1.0)) is True


def test_there_is_no_default_threshold() -> None:
    import inspect

    parameter = inspect.signature(ConsensusThreshold).parameters["required_share"]
    assert parameter.default is inspect.Parameter.empty, "a default threshold is a default quorum"
    mandate_parameter = inspect.signature(ConsensusThreshold.from_mandate).parameters[
        "required_share"
    ]
    assert mandate_parameter.default is inspect.Parameter.empty


def test_no_module_supplies_a_hardcoded_threshold() -> None:
    """The W8 obligation: "fails when a default threshold is used" — checked, not trusted."""
    import re

    from tests.unit.consensus_analysis_contract_helpers import SRC

    offenders = [
        path.relative_to(SRC).as_posix()
        for path in SRC.rglob("*.py")
        if re.search(r"ConsensusThreshold\(\s*[0-9]", path.read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"hardcoded threshold in {offenders}"
