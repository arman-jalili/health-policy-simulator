"""Contract freeze: phase monotonicity (issue #282, implements #286)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    enum_values,
    method_names,
    parameter_names,
)

from negotiation_session.domain.errors import ClosedRunImmutable, PhaseRegression
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import NegotiationPhase


def test_phase_order_is_declared_and_closed_is_last() -> None:
    assert [phase.value for phase in NegotiationPhase] == [
        "draft",
        "position_formation",
        "debate",
        "negotiation",
        "compromise",
        "closed",
    ]
    assert NegotiationPhase.CLOSED.value == "closed"
    assert enum_values(NegotiationPhase) >= {"draft", "closed"}


def test_phase_exposes_monotonic_helpers() -> None:
    assert isinstance(vars(NegotiationPhase)["rank"], property)
    assert isinstance(vars(NegotiationPhase)["is_terminal"], property)
    assert "can_advance_to" in method_names(NegotiationPhase)
    assert parameter_names(NegotiationPhase.can_advance_to) == ["self", "target"]


def test_aggregate_exposes_the_only_phase_transition_seam() -> None:
    assert "advance_phase" in method_names(SimulationRun)
    assert parameter_names(SimulationRun.advance_phase) == ["self", "target"]


def test_phase_violations_have_stable_codes() -> None:
    assert PhaseRegression.code == "PHASE_REGRESSION"
    assert ClosedRunImmutable.code == "CLOSED_RUN_IMMUTABLE"
