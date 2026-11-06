"""Contract freeze + machine-checked service classification (issue #331, implements #334).

Every service of the context is classified in ``SERVICE_CLASSIFICATION``; these checks prove the
declared layer is the layer that actually owns the class, that every port is an application-layer
protocol with an infrastructure adapter, and that each use case names exactly the ports it takes.
The three read use cases are implemented; the writing ones stay stubs until their gates land.
"""

from __future__ import annotations

import ast
import inspect
from datetime import UTC, date, datetime
from typing import Any, Protocol, cast

import pytest
from tests.unit.decision_brief_contract_helpers import (
    SRC,
    imported_modules,
    method_names,
    parameter_names,
)

from decision_brief.application import ports as application_ports
from decision_brief.application.commands import (
    GetDecisionBriefRequest,
    ListBriefVersionsRequest,
    ListCitationsRequest,
)
from decision_brief.application.services import (
    GetDecisionBrief,
    ListBriefVersions,
    ListCitations,
    PublishDecisionBrief,
    VersionDecisionBrief,
)
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import BriefNotFound, BriefNotPublished
from decision_brief.domain.services import (
    SERVICE_CLASSIFICATION,
    BriefProjectionBuilder,
    OutcomeHonestyPolicy,
    ReproductionChecker,
)
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    SECTION_ORDINAL,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitationProvenance,
    CitationReference,
    CitedStatement,
    EvidenceStatus,
    PassageId,
    RunId,
    SectionKind,
    SimulationDisclaimer,
)
from decision_brief.infrastructure import acl as infrastructure_acl
from decision_brief.interfaces import renderer as interface_renderer

APPLICATION_SERVICES = (
    PublishDecisionBrief,
    VersionDecisionBrief,
    GetDecisionBrief,
    ListBriefVersions,
    ListCitations,
)

DOMAIN_SERVICES = (BriefProjectionBuilder, ReproductionChecker, OutcomeHonestyPolicy)

DISCLAIMER = SimulationDisclaimer(
    text=DEFAULT_DISCLAIMER_TEXT,
    model_reference="openai/gpt-5.1",
    prompt_version="brief.v3",
)


# ── Classification ────────────────────────────────────────────────────────────────


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


def _classes_by_layer() -> dict[str, set[str]]:
    """Which class names each layer directory of the module defines."""
    found: dict[str, set[str]] = {}
    for path in SRC.rglob("*.py"):
        layer = path.relative_to(SRC).parts[0]
        if layer in {"domain", "application", "infrastructure", "interfaces"}:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = found.setdefault(layer, set())
            names.update(node.name for node in tree.body if isinstance(node, ast.ClassDef))
    return found


def test_each_classified_service_is_defined_in_its_declared_layer() -> None:
    classes = _classes_by_layer()
    for name, layer in SERVICE_CLASSIFICATION.items():
        if layer == "infrastructure":
            continue  # the port is declared in application/, the adapter in infrastructure/
        assert name in classes.get(layer, set()), f"{name} is classified {layer}"


def test_the_ports_are_application_layer_runtime_protocols() -> None:
    ports = (
        "CitationResolver",
        "ProvenanceDisclosureGate",
        "RunHistorySource",
        "ConsensusSource",
    )
    for name in ports:
        port = getattr(application_ports, name)
        assert issubclass(port, Protocol), name
        assert getattr(port, "_is_runtime_protocol", False), name


def test_each_infrastructure_service_has_an_adapter_with_the_port_method() -> None:
    adapters = [
        member
        for _, member in inspect.getmembers(infrastructure_acl, inspect.isclass)
        if member.__module__ == infrastructure_acl.__name__
    ]
    for port_name in ("CitationResolver", "ProvenanceDisclosureGate"):
        port = getattr(application_ports, port_name)
        method = next(
            name
            for name, member in inspect.getmembers(port, inspect.isfunction)
            if not name.startswith("_")
        )
        expected = parameter_names(getattr(port, method))
        assert any(
            hasattr(adapter, method) and parameter_names(getattr(adapter, method)) == expected
            for adapter in adapters
        ), f"no adapter implements {port_name}.{method}"


def test_each_use_case_names_exactly_the_ports_it_takes() -> None:
    for service in APPLICATION_SERVICES:
        ports = [name for name in parameter_names(service.__init__) if name != "self"]
        # Ports are stubs here on purpose: the collaborator list, not the behaviour, is under test.
        instance = cast(Any, service)(**dict.fromkeys(ports))
        assert len(instance.collaborators()) == len(ports), service.__name__


def test_application_services_expose_one_execute_boundary() -> None:
    for service in APPLICATION_SERVICES:
        assert "execute" in method_names(service), service.__name__


def test_domain_service_contracts_are_single_method_runtime_protocols() -> None:
    for service in DOMAIN_SERVICES:
        assert issubclass(service, Protocol), service.__name__
        assert getattr(service, "_is_runtime_protocol", False), service.__name__
        methods = [
            name
            for name, member in inspect.getmembers(service, inspect.isfunction)
            if not name.startswith("_")
        ]
        assert len(methods) == 1, service.__name__


def test_the_renderer_is_the_interface_layer_service() -> None:
    assert issubclass(interface_renderer.BriefRenderer, Protocol)
    assert "render" in dir(interface_renderer.BriefRenderer)


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


# ── The read use cases are implemented, not stubs (#334) ─────────────────────────


def _citation(passage_id: str) -> CitationReference:
    return CitationReference(
        passage_id=PassageId(passage_id),
        provenance=CitationProvenance(
            outlet="Der Standard",
            published_on=date(2026, 1, 2),
            medium="print",
            page_from=1,
            page_to=2,
            source_uri="https://example.test/a",
        ),
    )


def _brief(*, version: int = 1, status: BriefStatus = BriefStatus.PUBLISHED) -> DecisionBrief:
    statement = CitedStatement(
        text="Waiting times rose by 12%.",
        status=EvidenceStatus.EVIDENCED,
        citations=(_citation("psg_01J"),),
    )
    sections = {
        kind: BriefSection(
            kind=kind,
            ordinal=SECTION_ORDINAL[kind],
            statements=(statement,) if kind is SectionKind.QUESTION else (),
        )
        for kind in SectionKind
    }
    return DecisionBrief(
        id=BriefId(f"brf_0{version}J"),
        run_id=RunId("run_01J"),
        version=BriefVersion(
            number=version,
            run_id=RunId("run_01J"),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
            previous_version=version - 1 if version > 1 else None,
            reason="correction" if version > 1 else None,
        ),
        sections=sections,
        disclaimer=DISCLAIMER,
        status=status,
    )


class FakeBriefs:
    """In-memory repository double: the service depends on the protocol, not on a database."""

    def __init__(self, *briefs: DecisionBrief) -> None:
        self._items = {str(brief.id): brief for brief in briefs}

    async def get(self, brief_id: BriefId) -> DecisionBrief | None:
        return self._items.get(str(brief_id))

    async def save(self, brief: DecisionBrief) -> None:
        self._items[str(brief.id)] = brief

    async def versions_for_run(self, run_id: RunId) -> list[DecisionBrief]:
        return sorted(
            (brief for brief in self._items.values() if brief.run_id == run_id),
            key=lambda brief: brief.version.number,
        )


async def test_get_decision_brief_returns_the_frozen_brief() -> None:
    brief = _brief()
    service = GetDecisionBrief(briefs=FakeBriefs(brief))

    result = await service.execute(GetDecisionBriefRequest(brief_id=brief.id))

    assert result.brief is brief
    assert result.citation_count == 1


async def test_get_decision_brief_reports_an_unknown_id() -> None:
    service = GetDecisionBrief(briefs=FakeBriefs())
    with pytest.raises(BriefNotFound):
        await service.execute(GetDecisionBriefRequest(brief_id=BriefId("brf_missing")))


async def test_list_brief_versions_returns_every_version_of_the_run() -> None:
    service = ListBriefVersions(briefs=FakeBriefs(_brief(version=1), _brief(version=2)))

    result = await service.execute(ListBriefVersionsRequest(run_id=RunId("run_01J")))

    assert [item.brief.version.number for item in result.items] == [1, 2]


async def test_list_citations_returns_the_brief_citations() -> None:
    brief = _brief()
    service = ListCitations(briefs=FakeBriefs(brief))

    result = await service.execute(ListCitationsRequest(brief_id=brief.id))

    assert [str(citation.passage_id) for citation in result.citations] == ["psg_01J"]
    assert result.citations[0].is_resolved() is True


async def test_list_citations_filters_by_section() -> None:
    brief = _brief()
    service = ListCitations(briefs=FakeBriefs(brief))

    ours = await service.execute(
        ListCitationsRequest(brief_id=brief.id, section=SectionKind.QUESTION)
    )
    other = await service.execute(
        ListCitationsRequest(brief_id=brief.id, section=SectionKind.IMPACT)
    )

    assert len(ours.citations) == 1
    assert other.citations == ()


async def test_list_citations_refuses_a_draft() -> None:
    brief = _brief(status=BriefStatus.DRAFT)
    service = ListCitations(briefs=FakeBriefs(brief))

    with pytest.raises(BriefNotPublished):
        await service.execute(ListCitationsRequest(brief_id=brief.id))


async def test_list_citations_reports_an_unknown_id() -> None:
    service = ListCitations(briefs=FakeBriefs())
    with pytest.raises(BriefNotFound):
        await service.execute(ListCitationsRequest(brief_id=BriefId("brf_missing")))
