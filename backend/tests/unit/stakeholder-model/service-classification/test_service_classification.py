"""Contract freeze: service classification and layer placement (ADR-008)."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from tests.unit.stakeholder_contract_helpers import SRC, imported_names, method_names

from stakeholder_model.application import ports, services
from stakeholder_model.domain import repositories
from stakeholder_model.domain import services as domain_services
from stakeholder_model.infrastructure.personas import PersonaFactory

APPLICATION_SERVICES = (
    services.RegisterStakeholder,
    services.UpdateStakeholderProfile,
    services.CitePowerSource,
    services.RecordHistoricalPosition,
    services.SelectRelevantStakeholders,
    services.BindAgentPersona,
    services.GetStakeholderProfile,
    services.ListStakeholders,
    services.ListHistoricalPositions,
    services.LoadPersonaCards,
    services.PublishInstitutionalAllowlist,
)


def test_application_services_orchestrate_io() -> None:
    for service in APPLICATION_SERVICES:
        assert service.__module__.startswith("stakeholder_model.application")
        assert inspect.iscoroutinefunction(service.execute)


def test_domain_services_are_pure_and_own_the_rules() -> None:
    for service in (
        domain_services.TopicOverlapScorer,
        domain_services.WeightedInterestScorer,
        domain_services.ExplicitAttribution,
        domain_services.ReportedAttribution,
        domain_services.MentionOnly,
    ):
        assert service.__module__.startswith("stakeholder_model.domain")

    assert not inspect.iscoroutinefunction(domain_services.TopicOverlapScorer.score)
    assert not inspect.iscoroutinefunction(domain_services.ExplicitAttribution.classify)
    assert inspect.iscoroutinefunction(repositories.StakeholderRepository.save)


def test_repository_protocols_are_domain_owned() -> None:
    for protocol in (
        repositories.StakeholderRepository,
        repositories.AgentBindingRepository,
        repositories.CorpusEvidencePort,
    ):
        assert protocol.__module__ == "stakeholder_model.domain.repositories"

    assert {
        "get",
        "save",
        "all_registered",
    } == method_names(repositories.StakeholderRepository)
    assert {"get_for_run", "save"} == method_names(repositories.AgentBindingRepository)
    assert {"passages_about"} == method_names(repositories.CorpusEvidencePort)


def test_vendor_and_downstream_capabilities_are_ports() -> None:
    for name in ("UnitOfWork", "Clock", "InstitutionalGuardPort", "PersonaLoaderPort"):
        assert hasattr(ports, name)
        assert getattr(ports, name).__module__ == "stakeholder_model.application.ports"


def test_persona_factory_is_an_infrastructure_adapter() -> None:
    assert PersonaFactory.__module__ == "stakeholder_model.infrastructure.personas"
    assert {"load_all", "load"} <= method_names(PersonaFactory)


def test_domain_layer_has_no_outward_imports() -> None:
    for path in (SRC / "domain").glob("*.py"):
        imports = " ".join(sorted(imported_names(path)))
        assert "stakeholder_model.application" not in imports
        assert "stakeholder_model.infrastructure" not in imports
        assert "stakeholder_model.interfaces" not in imports


def test_application_services_depend_on_ports_not_adapters() -> None:
    imports = " ".join(sorted(imported_names(SRC / "application" / "services.py")))

    assert "stakeholder_model.infrastructure" not in imports
    assert "stakeholder_model.interfaces" not in imports
    assert "sqlalchemy" not in imports
    assert "fastapi" not in imports


def test_register_service_constructor_uses_ports() -> None:
    hints = get_type_hints(services.RegisterStakeholder.__init__)

    assert hints["repository"] is repositories.StakeholderRepository
    assert hints["unit_of_work"] is ports.UnitOfWork
    assert hints["clock"] is ports.Clock


def test_service_names_match_the_canonical_use_cases() -> None:
    application_names = {
        name
        for name, value in vars(services).items()
        if inspect.isclass(value) and value.__module__ == services.__name__
    }

    assert {
        "RegisterStakeholder",
        "BindAgentPersona",
        "SelectRelevantStakeholders",
        "RecordHistoricalPosition",
    } <= application_names
    assert "RegisterStakeholder" not in {
        name for name in vars(domain_services) if not name.startswith("_")
    }
