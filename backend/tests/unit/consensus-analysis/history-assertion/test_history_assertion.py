"""Contract freeze: history assertion (issue #305, implements #311)."""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.errors import StanceNotInHistory
from consensus_analysis.domain.values import (
    ConsensusId,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    StakeholderId,
    Stance,
    StanceSnapshot,
    TopicRef,
)


def test_absence_from_the_log_is_a_stable_error_code() -> None:
    assert StanceNotInHistory.code == "STANCE_NOT_IN_HISTORY"
    assert StanceNotInHistory.status_code == 422


def test_a_snapshot_carries_its_log_provenance() -> None:
    assert field_names(StanceSnapshot) == [
        "stakeholder",
        "stance",
        "topic",
        "weight",
        "recorded",
        "log_position",
    ]
    unrecorded = StanceSnapshot(
        stakeholder=StakeholderId("stk_1"),
        stance=Stance.SUPPORT,
        recorded=False,
        topic=TopicRef("waiting_times"),
    )
    assert unrecorded.recorded is False
    assert unrecorded.log_position is None


def test_the_assertion_is_a_named_record_member() -> None:
    assert parameter_names(ConsensusRecord.assert_stances_recorded) == ["self"]


def _record(stances: dict[StakeholderId, StanceSnapshot]) -> ConsensusRecord:
    return ConsensusRecord.open(
        consensus_id=ConsensusId("cns_1"),
        run_id=RunId("run_1"),
        topic=TopicRef("waiting_times"),
        proposal_class=ProposalClass.SERVICE_CATALOGUE,
        threshold=ConsensusThreshold(0.5),
        stances=stances,
        vetoes={},
        log_position=LogPosition(0),
    )


def test_a_recorded_stance_passes_the_assertion() -> None:
    stakeholder = StakeholderId("stk_1")
    record = _record(
        {
            stakeholder: StanceSnapshot(
                stakeholder=stakeholder,
                stance=Stance.SUPPORT,
                topic=TopicRef("waiting_times"),
                recorded=True,
                log_position=LogPosition(7),
            )
        }
    )
    record.assert_stances_recorded()


def test_a_recorded_stance_without_a_log_position_cannot_be_constructed() -> None:
    """Invariant 2 at construction time: provenance is not optional."""
    with pytest.raises(ValueError, match="log position"):
        StanceSnapshot(
            stakeholder=StakeholderId("stk_1"),
            stance=Stance.SUPPORT,
            recorded=True,
            topic=TopicRef("waiting_times"),
        )


def test_every_offending_stance_is_named_not_just_the_first() -> None:
    record = _record(
        {
            StakeholderId("stk_a"): StanceSnapshot(
                stakeholder=StakeholderId("stk_a"),
                stance=Stance.SUPPORT,
                recorded=False,
                topic=TopicRef("waiting_times"),
            ),
            StakeholderId("stk_b"): StanceSnapshot(
                stakeholder=StakeholderId("stk_b"),
                stance=Stance.OPPOSE,
                recorded=False,
                topic=TopicRef("waiting_times"),
            ),
        }
    )
    with pytest.raises(StanceNotInHistory) as raised:
        record.assert_stances_recorded()
    assert raised.value.missing == ("stk_a", "stk_b")
    assert len(raised.value.details) == 2


def test_an_unrecorded_stance_fails_the_assertion_with_its_id() -> None:
    stakeholder = StakeholderId("stk_ghost")
    record = _record(
        {
            stakeholder: StanceSnapshot(
                stakeholder=stakeholder,
                stance=Stance.SUPPORT,
                recorded=False,
                topic=TopicRef("waiting_times"),
            )
        }
    )
    with pytest.raises(StanceNotInHistory) as raised:
        record.assert_stances_recorded()
    assert raised.value.missing == ("stk_ghost",)
    assert raised.value.code == "STANCE_NOT_IN_HISTORY"
