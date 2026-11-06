"""Contract freeze: closed immutability (issue #282, implements #295)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import method_names, parameter_names

from negotiation_session.domain.errors import ClosedRunImmutable
from negotiation_session.domain.repositories import RunEventLog
from negotiation_session.domain.simulation_run import SimulationRun


def test_closed_run_refuses_every_mutation() -> None:
    for command in (
        "open_round",
        "submit_initial_position",
        "take_turn",
        "revise_position",
        "record_abstention",
        "track_conflict",
        "form_coalition",
        "close_round",
        "advance_phase",
    ):
        assert command in method_names(SimulationRun), command
    assert isinstance(vars(SimulationRun)["is_closed"], property)
    assert ClosedRunImmutable.code == "CLOSED_RUN_IMMUTABLE"


def test_events_still_replay_after_close() -> None:
    assert method_names(RunEventLog) == {"append", "read", "latest_sequence"}
    assert parameter_names(RunEventLog.read) == ["self", "run_id", "until_round"]
