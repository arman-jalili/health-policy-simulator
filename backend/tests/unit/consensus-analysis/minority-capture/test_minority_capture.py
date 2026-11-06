"""Contract freeze: minority capture (issue #305, implements #316)."""

from __future__ import annotations

import pytest
from tests.unit.consensus_analysis_contract_helpers import field_names, parameter_names

from consensus_analysis.domain.consensus_record import ConsensusRecord
from consensus_analysis.domain.entities import MajorityPosition, MinorityPosition
from consensus_analysis.domain.events import MinorityPositionRecorded
from consensus_analysis.domain.services import MajorityHolds, MinorityCapture
from consensus_analysis.domain.values import StakeholderId, SupportLevel


def test_a_minority_position_names_its_holders_and_their_reasons() -> None:
    assert field_names(MinorityPosition) == ["holders", "objections", "proposal"]
    position = MinorityPosition(
        holders=(StakeholderId("stk_1"),),
        objections=("scope too narrow",),
        proposal="extend the service catalogue",
    )
    assert position.covers((StakeholderId("stk_1"),)) is True
    assert position.covers((StakeholderId("stk_2"),)) is False


def test_a_minority_position_cannot_be_empty() -> None:
    with pytest.raises(ValueError, match="holders"):
        MinorityPosition(holders=(), objections=())


def test_capture_is_a_named_domain_service() -> None:
    assert parameter_names(MinorityCapture.capture) == [
        "self",
        "stances",
        "objections",
        "proposal",
    ]
    with pytest.raises(NotImplementedError, match="#316"):
        MinorityCapture().capture(stances={})


def test_majority_recording_is_separate_from_minority_capture() -> None:
    assert field_names(MajorityPosition) == ["proposal", "supporters", "support"]
    assert parameter_names(MajorityHolds.majority_of) == ["self", "proposal", "stances"]
    with pytest.raises(NotImplementedError, match="#316"):
        MajorityHolds().majority_of(proposal="extend the catalogue", stances={})


def test_the_record_can_attach_a_minority() -> None:
    assert parameter_names(ConsensusRecord.record_minority) == ["self", "position"]
    assert MinorityPositionRecorded.name == "MinorityPositionRecorded"
    assert field_names(MinorityPositionRecorded) == [
        "run_id",
        "topic",
        "holders",
        "objection_count",
    ]


def test_entity_factories_are_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError, match="#316"):
        MinorityPosition.record(holders=(StakeholderId("stk_1"),))
    with pytest.raises(NotImplementedError, match="#316"):
        MajorityPosition.carry(
            proposal="extend the catalogue",
            supporters=(),
            support=SupportLevel(value=0.0),
        )
