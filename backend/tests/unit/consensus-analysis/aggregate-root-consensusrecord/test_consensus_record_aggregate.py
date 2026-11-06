"""Contract freeze: aggregate root ``ConsensusRecord`` (issue #305, implements #306)."""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.values import (
    ConsensusId,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    TopicRef,
)


def test_aggregate_fields_are_frozen() -> None:
    assert field_names(ConsensusRecord) == [
        "id",
        "run_id",
        "topic",
        "proposal_class",
        "threshold",
        "stances",
        "vetoes",
        "log_position",
        "outcome",
        "majority",
        "minorities",
        "unresolved",
        "events",
    ]


def test_aggregate_exposes_the_frozen_derivation_surface() -> None:
    for name in (
        "open",
        "determine",
        "assert_stances_recorded",
        "record_minority",
        "declare_unresolved",
        "drain_events",
        "digest",
        "minority_holders",
        "supporting_stakeholders",
        "ordered_stances",
    ):
        assert callable(getattr(ConsensusRecord, name)), name


def test_open_signature_is_frozen() -> None:
    assert parameter_names(ConsensusRecord.open) == [
        "consensus_id",
        "run_id",
        "topic",
        "proposal_class",
        "threshold",
        "stances",
        "vetoes",
        "log_position",
    ]


def test_stub_names_the_implementing_issue() -> None:
    record = ConsensusRecord(
        id=ConsensusId("cns_1"),
        run_id=RunId("run_1"),
        topic=TopicRef("waiting_times"),
        proposal_class=ProposalClass.SERVICE_CATALOGUE,
        threshold=ConsensusThreshold(0.5),
        stances={},
        vetoes={},
        log_position=LogPosition(0),
    )
    with pytest.raises(NotImplementedError, match="#306"):
        record.determine()


def test_helpers_never_upgrade_a_partial_result() -> None:
    record = ConsensusRecord(
        id=ConsensusId("cns_1"),
        run_id=RunId("run_1"),
        topic=TopicRef("waiting_times"),
        proposal_class=ProposalClass.SERVICE_CATALOGUE,
        threshold=ConsensusThreshold(0.5),
        stances={},
        vetoes={},
        log_position=LogPosition(0),
    )
    assert record.minority_holders() == ()
    assert record.supporting_stakeholders() == ()
    assert record.ordered_stances() == ()
