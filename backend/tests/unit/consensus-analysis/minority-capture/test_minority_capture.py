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
    assert MinorityCapture().capture(stances={}) == ()


def test_every_disapproving_stakeholder_gets_its_own_position() -> None:
    from consensus_analysis.domain.values import LogPosition, Stance, StanceSnapshot

    def snapshot(key: str, stance: Stance, position: int) -> tuple[StakeholderId, StanceSnapshot]:
        stakeholder = StakeholderId(key)
        return stakeholder, StanceSnapshot(
            stakeholder=stakeholder,
            stance=stance,
            log_position=LogPosition(position),
        )

    stances = dict(
        [
            snapshot("stk_1", Stance.SUPPORT, 0),
            snapshot("stk_2", Stance.OPPOSE, 1),
            snapshot("stk_3", Stance.QUALIFY, 2),
            snapshot("stk_4", Stance.ABSTAIN, 3),
        ]
    )
    positions = MinorityCapture().capture(
        stances=stances, objections={StakeholderId("stk_2"): "too narrow"}
    )
    assert [position.holders for position in positions] == [
        (StakeholderId("stk_2"),),
        (StakeholderId("stk_3"),),
    ]
    assert positions[0].objections == ("too narrow",)
    assert positions[1].objections == ()


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


def test_entity_factories_record_what_they_are_given() -> None:
    position = MinorityPosition.record(
        holders=(StakeholderId("stk_1"),), objections=("scoped too narrowly",), proposal="x"
    )
    assert position.holders == (StakeholderId("stk_1"),)
    assert position.objections == ("scoped too narrowly",)
    assert position.covers((StakeholderId("stk_1"),)) is True


def test_no_supporters_means_no_majority() -> None:
    with pytest.raises(ValueError, match="supporter"):
        MajorityPosition.carry(
            proposal="extend the catalogue",
            supporters=(),
            support=SupportLevel(value=0.0),
        )
    majority = MajorityPosition.carry(
        proposal="extend the catalogue",
        supporters=(StakeholderId("stk_1"),),
        support=SupportLevel(value=0.6),
    )
    assert majority.supporters == (StakeholderId("stk_1"),)
