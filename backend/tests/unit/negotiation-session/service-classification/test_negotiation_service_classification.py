"""Contract freeze: service classification (issue #282, implements #285)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import method_names

from negotiation_session.application.services import (
    SERVICE_CLASSIFICATION,
    CloseRound,
    FormCoalition,
    GetSimulationRun,
    ListConflictTopics,
    ListRoundLearning,
    ListRounds,
    OpenSimulationRun,
    RecordAbstention,
    ReplaySimulationHistory,
    RevisePosition,
    SelectRelevantStakeholders,
    SubmitInitialPosition,
    SummariseIntermediateResult,
    TakeNegotiationTurn,
    TrackConflictTopic,
    TranslateQuestionToMandate,
)
from negotiation_session.domain.services import (
    DetectArgumentContradiction,
    EvaluateStoppingCondition,
)

APPLICATION_SERVICES = (
    TranslateQuestionToMandate,
    SelectRelevantStakeholders,
    OpenSimulationRun,
    SubmitInitialPosition,
    TakeNegotiationTurn,
    RevisePosition,
    RecordAbstention,
    TrackConflictTopic,
    FormCoalition,
    CloseRound,
    GetSimulationRun,
    ListRounds,
    ListConflictTopics,
    ListRoundLearning,
    SummariseIntermediateResult,
    ReplaySimulationHistory,
)


def test_every_application_service_is_classified() -> None:
    assert set(SERVICE_CLASSIFICATION) == {
        *(service.__name__ for service in APPLICATION_SERVICES),
        "EvaluateStoppingCondition",
        "DetectArgumentContradiction",
        "TurnOrderPolicy",
    }
    for service in APPLICATION_SERVICES:
        assert SERVICE_CLASSIFICATION[service.__name__] == "application"


def test_rule_evaluation_belongs_to_the_domain_layer() -> None:
    assert SERVICE_CLASSIFICATION["EvaluateStoppingCondition"] == "domain"
    assert SERVICE_CLASSIFICATION["DetectArgumentContradiction"] == "domain"
    assert SERVICE_CLASSIFICATION["TurnOrderPolicy"] == "domain"
    assert method_names(EvaluateStoppingCondition) == {"evaluate"}
    assert method_names(DetectArgumentContradiction) == {"detect", "contradicts"}


def test_application_services_expose_one_execute_boundary() -> None:
    for service in APPLICATION_SERVICES:
        assert "execute" in method_names(service), service.__name__
