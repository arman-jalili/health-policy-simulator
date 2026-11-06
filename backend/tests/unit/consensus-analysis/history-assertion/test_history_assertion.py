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
        "weight",
        "recorded",
        "log_position",
    ]
    unrecorded = StanceSnapshot(
        stakeholder=StakeholderId("stk_1"), stance=Stance.SUPPORT, recorded=False
    )
    assert unrecorded.recorded is False
    assert unrecorded.log_position is None


def test_the_assertion_is_a_named_record_member() -> None:
    assert parameter_names(ConsensusRecord.assert_stances_recorded) == ["self"]


def test_the_assertion_is_not_implemented_yet() -> None:
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
    with pytest.raises(NotImplementedError, match="#311"):
        record.assert_stances_recorded()
