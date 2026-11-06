"""Contract freeze: service classification and layer boundaries (issue #331, implements #338)."""

from __future__ import annotations

from tests.unit.decision_brief_contract_helpers import (
    imported_modules,
    method_names,
)

from decision_brief.application.services import (
    GetDecisionBrief,
    ListBriefVersions,
    ListCitations,
    PublishDecisionBrief,
    VersionDecisionBrief,
)
from decision_brief.domain.services import (
    SERVICE_CLASSIFICATION,
    BriefProjectionBuilder,
    OutcomeHonestyPolicy,
    ReproductionChecker,
)

APPLICATION_SERVICES = (
    PublishDecisionBrief,
    VersionDecisionBrief,
    GetDecisionBrief,
    ListBriefVersions,
    ListCitations,
)

DOMAIN_SERVICES = (BriefProjectionBuilder, ReproductionChecker, OutcomeHonestyPolicy)


def test_every_service_is_classified() -> None:
    assert set(SERVICE_CLASSIFICATION) == {
        *(service.__name__ for service in APPLICATION_SERVICES),
        *(service.__name__ for service in DOMAIN_SERVICES),
        "CitationResolver",
        "ProvenanceDisclosureGate",
        "BriefRenderer",
    }


def test_use_cases_belong_to_the_application_layer() -> None:
    for service in APPLICATION_SERVICES:
        assert SERVICE_CLASSIFICATION[service.__name__] == "application", service.__name__


def test_projection_and_gates_belong_to_the_domain_layer() -> None:
    for service in DOMAIN_SERVICES:
        assert SERVICE_CLASSIFICATION[service.__name__] == "domain", service.__name__


def test_adapters_and_renderer_are_classified_outside_the_domain() -> None:
    assert SERVICE_CLASSIFICATION["CitationResolver"] == "infrastructure"
    assert SERVICE_CLASSIFICATION["ProvenanceDisclosureGate"] == "infrastructure"
    assert SERVICE_CLASSIFICATION["BriefRenderer"] == "interfaces"


def test_application_services_expose_one_execute_boundary() -> None:
    for service in APPLICATION_SERVICES:
        assert "execute" in method_names(service), service.__name__


def test_every_use_case_publishes_its_collaborators() -> None:
    """A stub that names its ports cannot silently lose one while it is still unimplemented."""
    for service in APPLICATION_SERVICES:
        assert "collaborators" in method_names(service), service.__name__


def test_the_application_layer_imports_no_framework_or_adapter() -> None:
    forbidden_prefixes = (
        "fastapi",
        "sqlalchemy",
        "pydantic",
        "decision_brief.infrastructure",
        "decision_brief.interfaces",
    )
    for name in ("commands", "dto", "ports", "services"):
        for module in imported_modules(f"application/{name}.py"):
            assert not module.startswith(forbidden_prefixes), f"application/{name}.py: {module}"
