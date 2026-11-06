"""Contract freeze: revision without cause (issue #282, implements #288)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from negotiation_session.application.services import RevisePosition
from negotiation_session.domain.errors import PositionNotFound, RevisionWithoutCause
from negotiation_session.domain.events import PositionRevised, PositionRevisionRejected
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import RevisionReason


def test_revision_reason_must_cite_something() -> None:
    assert field_names(RevisionReason) == ["argument_ids", "pack_ids", "driver"]
    assert parameter_names(RevisionReason.cites) == ["self", "argument_ids", "pack_ids"]


def test_aggregate_and_service_expose_the_revision_seam() -> None:
    assert parameter_names(SimulationRun.revise_position) == [
        "self",
        "stakeholder",
        "topic",
        "stance",
        "reason",
    ]
    assert "revise_position" in method_names(SimulationRun)
    assert parameter_names(RevisePosition.execute) == ["self", "request"]


def test_rejection_and_revision_are_both_audited_events() -> None:
    assert field_names(PositionRevised) == [
        "run_id",
        "round",
        "stakeholder_id",
        "topic",
        "position_id",
        "from_stance",
        "to_stance",
        "argument_ids",
        "pack_ids",
    ]
    assert field_names(PositionRevisionRejected) == [
        "run_id",
        "stakeholder_id",
        "topic",
        "reason_code",
    ]
    assert PositionRevisionRejected.name == "PositionRevisionRejected"


def test_revision_errors_have_stable_codes() -> None:
    assert RevisionWithoutCause.code == "REVISION_WITHOUT_CAUSE"
    assert PositionNotFound.code == "POSITION_NOT_FOUND"
