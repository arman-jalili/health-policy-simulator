"""Contract freeze: owned entities and value objects (issue #282, implements #284)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    enum_values,
    field_names,
    method_names,
    parameter_names,
)

from negotiation_session.domain.entities import (
    Argument,
    Coalition,
    CoalitionOffer,
    ConflictTopic,
    NegotiationMandate,
    NegotiationRound,
    Position,
    RoundLearning,
)
from negotiation_session.domain.values import (
    ArgumentStance,
    CoalitionOfferStatus,
    ConflictStatus,
    LearningInsightType,
    NegotiationPhase,
    Proposal,
    ProposalComponent,
    ProposalQuantification,
    RevisionReason,
    StoppingCondition,
    TurnAssignment,
    TurnOutcome,
)


def test_entities_are_identified_owned_objects() -> None:
    assert field_names(NegotiationMandate)[:8] == [
        "id",
        "question",
        "objective",
        "constraints",
        "round_cap",
        "stopping_conditions",
        "profile_version",
        "phase",
    ]
    assert field_names(Position)[:8] == [
        "id",
        "stakeholder",
        "topic",
        "stance",
        "proposal",
        "evidence",
        "round_number",
        "revision",
    ]
    assert field_names(Argument)[:7] == [
        "id",
        "stakeholder",
        "target",
        "stance",
        "text",
        "claims",
        "evidence",
    ]
    assert field_names(ConflictTopic)[:3] == ["id", "topic", "status"]
    assert field_names(CoalitionOffer)[:4] == ["id", "coalition_id", "invited", "conditions"]
    assert field_names(Coalition)[:3] == ["id", "topic", "proposal"]
    assert field_names(RoundLearning)[:3] == ["id", "round_number", "insights"]
    assert field_names(NegotiationRound)[:4] == ["id", "number", "turn_order", "positions"]


def test_value_objects_are_immutable_by_value() -> None:
    assert field_names(ProposalComponent)[:5] == [
        "measure",
        "effect",
        "population",
        "cost_eur",
        "quantification",
    ]
    assert field_names(Proposal) == ["summary", "components"]
    assert field_names(RevisionReason) == ["argument_ids", "pack_ids", "driver"]
    assert field_names(TurnAssignment) == ["stakeholder", "topic", "order", "outcome"]
    assert field_names(StoppingCondition) == ["name", "fired", "parameters"]
    assert parameter_names(StoppingCondition.evaluate) == [
        "consensus",
        "rounds_done",
        "round_cap",
        "deadlocked",
    ]


def test_vocabulary_is_closed() -> None:
    assert enum_values(NegotiationPhase) == {
        "draft",
        "position_formation",
        "debate",
        "negotiation",
        "compromise",
        "closed",
    }
    assert enum_values(ArgumentStance) == {
        "support",
        "oppose",
        "qualify",
        "conditional_accept",
    }
    assert enum_values(ProposalQuantification) == {"quantified", "unquantified"}
    assert enum_values(LearningInsightType) == {
        "shared_interest",
        "blocking_constraint",
        "evidence_gap",
        "coalition_signal",
        "position_shift",
    }
    assert enum_values(ConflictStatus) == {"open", "resolved", "deadlocked"}
    assert enum_values(CoalitionOfferStatus) == {"offered", "accepted", "declined"}
    assert enum_values(TurnOutcome) == {"pending", "spoke", "abstained"}


def test_entity_behaviour_surface_is_frozen() -> None:
    assert method_names(Position) >= {"initial", "supersede"}
    assert method_names(Argument) >= {"new"}
    assert method_names(ConflictTopic) >= {"open", "record_stance"}
    assert method_names(CoalitionOffer) >= {"offer", "accept", "decline"}
    assert method_names(Coalition) >= {"form", "add_member"}
    assert method_names(RoundLearning) >= {"capture", "to_prompt_payload"}
    assert method_names(NegotiationRound) >= {
        "open",
        "record_position",
        "record_argument",
        "record_abstention",
        "attach_learning",
        "close",
        "carry_learning",
        "open_position_for",
    }
