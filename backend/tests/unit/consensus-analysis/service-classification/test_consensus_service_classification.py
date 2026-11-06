"""Service classification, mechanically verified (issues #305, #308).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Service classification)

``SERVICE_CLASSIFICATION`` is not a comment: every entry is resolved to the class that actually
implements it, and that class must live in the layer the classification names. A rule that drifts
from ``domain/`` into ``application/`` fails here instead of being discovered in review.
"""

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


# ── issue #308: the classification is checkable, not aspirational ─────────────────────────────


def _resolve(name: str) -> type:
    import importlib

    for module_name in (
        "consensus_analysis.application.services",
        "consensus_analysis.domain.services",
        "consensus_analysis.application.ports",
    ):
        module = importlib.import_module(module_name)
        candidate = getattr(module, name, None)
        if isinstance(candidate, type):
            return candidate
    raise AssertionError(f"{name} is classified but not importable")


def test_every_classified_service_lives_in_the_layer_it_is_classified_into() -> None:
    for name, layer in SERVICE_CLASSIFICATION.items():
        if name == "ProjectionRebuilder":
            continue  # a port, see the next test
        resolved = _resolve(name)
        assert resolved.__module__.startswith(f"consensus_analysis.{layer}."), (
            name,
            resolved.__module__,
            layer,
        )


def test_the_rebuild_strategy_is_a_port_whose_adapter_belongs_to_infrastructure() -> None:
    """Dependency inversion: consumed by ``application/``, implemented in ``infrastructure/``."""
    from consensus_analysis.application.ports import ProjectionRebuilder

    assert getattr(ProjectionRebuilder, "_is_protocol", False) is True
    assert ProjectionRebuilder.__module__ == "consensus_analysis.application.ports"
    assert SERVICE_CLASSIFICATION["ProjectionRebuilder"] == "infrastructure"


def test_no_rule_logic_is_implemented_in_the_application_layer() -> None:
    """The rule surface is domain-owned; an application copy is exactly the drift #308 prevents."""
    from consensus_analysis.application import services as application_services

    forbidden = {
        "SupportLevel",
        "ConsensusThreshold",
        "ConsensusRule",
        "NotVetoed",
        "ThresholdMet",
        "MinorityCapture",
    }
    assert forbidden & set(vars(application_services)) == set()


def test_the_classification_names_only_services_that_exist() -> None:
    for name in SERVICE_CLASSIFICATION:
        assert isinstance(_resolve(name), type), name
