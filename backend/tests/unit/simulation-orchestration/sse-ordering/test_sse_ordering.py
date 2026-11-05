"""Contract freeze: SSE ordering (issue #205)."""

from __future__ import annotations

import inspect

from tests.unit.simulation_orchestration_contract_helpers import (
    enum_values,
    field_names,
    method_names,
    parameter_names,
)

from simulation_orchestration.application.dto import ProgressEventView
from simulation_orchestration.application.repositories import ProgressStore
from simulation_orchestration.application.services import StreamSimulationProgress
from simulation_orchestration.application.values import ProgressKind


def test_progress_event_has_monotonic_sequence_and_replay_id() -> None:
    assert field_names(ProgressEventView) == [
        "event_id",
        "run_id",
        "sequence",
        "kind",
        "payload",
        "created_at",
    ]
    assert enum_values(ProgressKind) >= {
        "run.started",
        "run.paused",
        "run.resumed",
        "run.completed",
        "run.failed",
        "run.budget_exhausted",
    }


def test_progress_store_replays_after_sequence() -> None:
    assert method_names(ProgressStore) == {"append", "latest_sequence", "list_after"}
    assert parameter_names(ProgressStore.list_after) == [
        "self",
        "run_id",
        "after_sequence",
        "limit",
    ]


def test_stream_returns_an_async_iterator() -> None:
    signature = inspect.signature(StreamSimulationProgress.execute)
    assert "AsyncIterator" in str(signature.return_annotation)
