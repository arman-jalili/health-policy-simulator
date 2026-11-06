"""Contract freeze: replay equivalence (issue #282, implements #296)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from negotiation_session.application.dto import HistoryEventResult, ReplayResult
from negotiation_session.application.services import ReplaySimulationHistory
from negotiation_session.domain.events import LoggedEvent
from negotiation_session.domain.repositories import RunEventLog


def test_run_log_is_ordered_by_a_per_run_ordinal() -> None:
    assert field_names(LoggedEvent) == ["sequence", "event", "occurred_at"]
    assert method_names(RunEventLog) == {"append", "read", "latest_sequence"}
    assert parameter_names(RunEventLog.append) == ["self", "run_id", "events"]
    assert parameter_names(RunEventLog.read) == ["self", "run_id", "until_round"]


def test_replay_returns_the_fold_and_the_event_history() -> None:
    assert field_names(ReplayResult) == ["run_id", "until_round", "events", "state"]
    assert field_names(HistoryEventResult) == [
        "sequence",
        "event_type",
        "payload",
        "occurred_at",
    ]
    assert parameter_names(ReplaySimulationHistory.execute) == ["self", "request"]
    assert parameter_names(ReplaySimulationHistory.__init__) == ["self", "runs", "event_log"]
