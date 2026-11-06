"""Contract freeze: service classification (issue #305, implements #308)."""

from __future__ import annotations

from tests.unit.consensus_analysis_contract_helpers import method_names

from consensus_analysis.application.services import (
    SERVICE_CLASSIFICATION,
    AssessImpact,
    CompareScenarios,
    ComposeCompromisePackage,
    DeriveConsensus,
    GetConsensus,
    HandleRunClosed,
    ListPackages,
    ListUnresolvedConflicts,
    RebuildProjections,
)
from consensus_analysis.domain.services import (
    ComponentsCompatible,
    ConsensusRule,
    EstimateValidator,
    FeasibilityGuard,
    IllustrativeValueGuard,
    MajorityHolds,
    MinorityCapture,
    NotVetoed,
    ThresholdMet,
)

APPLICATION_SERVICES = (
    DeriveConsensus,
    GetConsensus,
    ListUnresolvedConflicts,
    ComposeCompromisePackage,
    ListPackages,
    AssessImpact,
    CompareScenarios,
    RebuildProjections,
    HandleRunClosed,
)

DOMAIN_SERVICES = (
    ConsensusRule,
    NotVetoed,
    ThresholdMet,
    MajorityHolds,
    MinorityCapture,
    ComponentsCompatible,
    EstimateValidator,
    IllustrativeValueGuard,
    FeasibilityGuard,
)


def test_every_service_is_classified() -> None:
    assert set(SERVICE_CLASSIFICATION) == {
        *(service.__name__ for service in APPLICATION_SERVICES),
        *(service.__name__ for service in DOMAIN_SERVICES),
        "ProjectionRebuilder",
    }


def test_use_cases_belong_to_the_application_layer() -> None:
    for service in APPLICATION_SERVICES:
        assert SERVICE_CLASSIFICATION[service.__name__] == "application", service.__name__


def test_rule_evaluation_belongs_to_the_domain_layer() -> None:
    for service in DOMAIN_SERVICES:
        assert SERVICE_CLASSIFICATION[service.__name__] == "domain", service.__name__


def test_projection_rebuild_belongs_to_the_infrastructure_layer() -> None:
    assert SERVICE_CLASSIFICATION["ProjectionRebuilder"] == "infrastructure"


def test_application_services_expose_one_execute_boundary() -> None:
    for service in APPLICATION_SERVICES:
        assert "execute" in method_names(service), service.__name__


def test_every_use_case_publishes_its_collaborators() -> None:
    """The frozen wiring contract: a stub that names its ports cannot silently lose one."""
    for service in APPLICATION_SERVICES:
        assert "collaborators" in method_names(service), service.__name__
