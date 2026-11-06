"""Contract freeze and wiring (issue #331, implements #345).

The router, the container shape and the composition factory are frozen; the app mounts the routes
and an unwired gate stops publication instead of being skipped (AC 11).
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from fastapi import Request
from tests.unit.decision_brief_contract_helpers import (
    SRC,
    annotation_names,
    domain_python_files,
    field_names,
    imported_modules,
    parameter_names,
)

from decision_brief.application.commands import PublishDecisionBriefRequest
from decision_brief.application.dto import CitationResolution
from decision_brief.application.services import PublishDecisionBrief
from decision_brief.composition import DecisionBriefContainer, build_container
from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import RejectedProposalRecord
from decision_brief.domain.errors import BriefGateUnavailable, BriefSourceIncomplete
from decision_brief.domain.projections import ConsensusProjection, RunProjection
from decision_brief.domain.services import SectionAssembler
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitationProvenance,
    CitationReference,
    RunId,
    SimulationDisclaimer,
)
from decision_brief.infrastructure.failclosed import (
    UnwiredCitationResolver,
    UnwiredConsensusSource,
    UnwiredHistorySource,
    UnwiredProjectionBuilder,
    UnwiredProvenanceGate,
)
from decision_brief.infrastructure.projection import BriefProjectionAdapter
from decision_brief.infrastructure.repository.memory import InMemoryDecisionBriefRepository
from decision_brief.infrastructure.runtime import NoopUnitOfWork, UuidFactory
from decision_brief.interfaces.http.deps import (
    DecisionBriefContainer as HttpContainer,
)
from decision_brief.interfaces.http.deps import get_container
from decision_brief.interfaces.http.router import router
from decision_brief.interfaces.renderer import JsonBriefRenderer
from identity_access.infrastructure.resolvers import StaticPrincipalResolver
from identity_access.interfaces.types import ROLE_SCOPES, Principal, Role
from shared.app import create_app
from shared.clock import SystemClock
from shared.config import Settings
from shared.enums import AuthMode, Persistence

"""Contract freeze and wiring (issue #331, implements #345).
The router, the container shape and the composition factory are frozen; the app mounts the routes
and an unwired gate stops publication instead of being skipped (AC 11).
"""
CONTAINER_FIELDS = [
    "publish_decision_brief",
    "version_decision_brief",
    "get_decision_brief",
    "list_brief_versions",
    "list_citations",
    "renderer",
]


def _routes() -> dict[tuple[str, str], Any]:
    return {
        (method, getattr(route, "path", "")): route
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_http_contract_is_exact() -> None:
    expected = {
        ("POST", "/api/v1/runs/{run_id}/brief"),
        ("GET", "/api/v1/briefs/{brief_id}"),
        ("GET", "/api/v1/runs/{run_id}/briefs"),
        ("POST", "/api/v1/briefs/{brief_id}:version"),
        ("GET", "/api/v1/briefs/{brief_id}/citations"),
    }
    assert set(_routes()) == expected


def test_publication_and_versioning_answer_201() -> None:
    routes = _routes()
    assert routes[("POST", "/api/v1/runs/{run_id}/brief")].status_code == 201
    assert routes[("POST", "/api/v1/briefs/{brief_id}:version")].status_code == 201


def test_every_route_declares_the_scope_the_gate_enforces() -> None:
    for (method, path), route in _routes().items():
        expected = "briefs:publish" if method == "POST" else "runs:read"
        assert route.openapi_extra == {"x-required-scope": expected}, path


def test_container_shape_is_frozen_in_both_representations() -> None:
    assert annotation_names(HttpContainer) == CONTAINER_FIELDS
    assert field_names(DecisionBriefContainer) == CONTAINER_FIELDS


def test_the_factory_names_every_port_and_requires_every_gate() -> None:
    assert parameter_names(build_container) == [
        "settings",
        "database",
        "disclaimer",
        "events",
        "clock",
        "ids",
        "uow",
        "briefs",
        "history",
        "consensus",
        "citations",
        "provenance",
        "projection",
        "renderer",
    ]
    parameters = inspect.signature(build_container).parameters
    for gate in ("citations", "provenance", "projection"):
        assert parameters[gate].default is inspect.Parameter.empty, gate


def test_an_unmounted_container_fails_closed() -> None:
    class _State:
        pass

    class _App:
        def __init__(self) -> None:
            self.state = _State()

    class _Request:
        def __init__(self) -> None:
            self.app = _App()

    with pytest.raises(BriefGateUnavailable):
        get_container(cast(Request, _Request()))


def test_the_domain_layer_imports_no_outer_layer_or_foreign_context() -> None:
    forbidden_prefixes = (
        "decision_brief.application",
        "decision_brief.infrastructure",
        "decision_brief.interfaces",
    )
    allowed_roots = {
        "__future__",
        "collections",
        "dataclasses",
        "datetime",
        "enum",
        "shared",
        "types",
        "typing",
    }
    for path in domain_python_files():
        relative = path.relative_to(SRC.parent).as_posix().removeprefix("decision_brief/")
        for module in imported_modules(relative):
            assert not module.startswith(forbidden_prefixes), f"{relative} imports {module}"
            assert module.split(".")[0] in allowed_roots or module.startswith(
                "decision_brief.domain"
            ), f"{relative} imports {module}"


# ── The router is mounted and an unwired gate stops publication (#345) ─────────────
DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"
ANALYST = Principal(label="analyst-1", role=Role.ANALYST, scopes=ROLE_SCOPES[Role.ANALYST])
ADMIN = Principal(label="admin-1", role=Role.ADMIN, scopes=ROLE_SCOPES[Role.ADMIN])


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        persistence=Persistence.MEMORY,
        auth_mode=AuthMode.STRICT,
    )


@pytest.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(_settings())
    app.state.identity_access = SimpleNamespace(
        principal_port=StaticPrincipalResolver({"analyst-key": ANALYST, "admin-key": ADMIN})
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def test_the_app_mounts_every_decision_brief_route() -> None:
    app = create_app(_settings())
    paths = set(app.openapi()["paths"])
    assert "/api/v1/runs/{run_id}/brief" in paths
    assert "/api/v1/briefs/{brief_id}" in paths
    assert "/api/v1/runs/{run_id}/briefs" in paths
    assert "/api/v1/briefs/{brief_id}:version" in paths
    assert "/api/v1/briefs/{brief_id}/citations" in paths


def test_the_app_binds_the_container() -> None:
    app = create_app(_settings())
    container = app.state.decision_brief
    assert container.publish_decision_brief is not None
    assert container.renderer.media_type == "application/json"


async def test_publication_fails_closed_while_the_provenance_gate_is_unwired(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/runs/run_01J/brief", headers={"X-API-Key": "admin-key"}
    )
    assert response.status_code == 503
    assert response.json()["code"] in {"BRIEF_GATE_UNAVAILABLE", "INTERNAL_ERROR"}


async def test_an_analyst_cannot_publish_a_brief(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/runs/run_01J/brief", headers={"X-API-Key": "analyst-key"}
    )
    assert response.status_code == 403


async def test_an_admin_can_attempt_publication(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/runs/run_01J/brief", headers={"X-API-Key": "admin-key"}
    )
    assert response.status_code != 403


# ── The publication path reaches the gates through the container (#345) ────────────
DISCLAIMER = SimulationDisclaimer(
    text=DEFAULT_DISCLAIMER_TEXT,
    model_reference="scripted-local",
    prompt_version="brief-projection.v1",
)
RUN = RunProjection(
    run_id=RunId("run_01J"),
    question="How should waiting times be reduced?",
    rejected_proposals=(
        RejectedProposalRecord(
            measure="Single payer fund",
            blocking_stakeholders=("Ärztekammer",),
            reasons=("no constitutional basis",),
        ),
    ),
    log_position=7,
    snapshot_ref="snap_01J",
)
CONSENSUS = ConsensusProjection(run_id=RunId("run_01J"), log_position=7)


class FakeHistory:
    def __init__(self, run: RunProjection | None) -> None:
        self._run = run

    async def load(self, run_id: RunId) -> RunProjection | None:
        return self._run


class FakeConsensus:
    def __init__(self, consensus: ConsensusProjection | None) -> None:
        self._consensus = consensus

    async def load(self, run_id: RunId) -> ConsensusProjection | None:
        return self._consensus


class FakeProvenance:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def assert_disclosed(self, run_id: RunId) -> None:
        self.calls.append(str(run_id))


class FakeCitations:
    async def resolve(self, passage_ids: Any) -> CitationResolution:
        return CitationResolution(
            resolved=tuple(
                CitationReference(
                    passage_id=passage_id,
                    provenance=CitationProvenance(
                        outlet="Der Standard",
                        published_on=datetime(2026, 1, 2, tzinfo=UTC).date(),
                        medium="print",
                        page_from=1,
                        page_to=2,
                        source_uri="https://example.test/a",
                    ),
                )
                for passage_id in passage_ids
            )
        )


class ProjectionAdapter:
    """Stands in for the projection-builder adapter the runtime will bind."""

    def build(
        self,
        *,
        run: RunProjection,
        consensus: ConsensusProjection,
        disclaimer: SimulationDisclaimer,
    ) -> DecisionBrief:
        brief = DecisionBrief(
            id=BriefId("brf_01J"),
            run_id=run.run_id,
            version=BriefVersion(
                number=1,
                run_id=run.run_id,
                snapshot_ref=run.snapshot_ref,
                generated_at=datetime(2026, 11, 6, tzinfo=UTC),
            ),
            sections=SectionAssembler().assemble(run=run, consensus=consensus),
            rejected_proposals=run.rejected_proposals,
            outcomes=SectionAssembler().outcomes(run, consensus),
            disclaimer=disclaimer,
        )
        return brief


class FakeEvents:
    def __init__(self) -> None:
        self.published: list[Any] = []

    async def publish(self, events: Any, *, trace_id: str | None = None) -> None:
        self.published.extend(events)


def _publish(
    *,
    history: Any,
    consensus: Any,
    provenance: Any,
    citations: Any,
    projection: Any,
    briefs: Any = None,
    events: Any = None,
) -> PublishDecisionBrief:
    return PublishDecisionBrief(
        briefs=briefs or InMemoryDecisionBriefRepository(),
        history=history,
        consensus=consensus,
        citations=citations,
        provenance=provenance,
        projection=projection,
        disclaimer=DISCLAIMER,
        events=events or FakeEvents(),
        clock=SystemClock(),
        ids=UuidFactory(),
        uow=NoopUnitOfWork(),
    )


async def test_an_unwired_provenance_gate_blocks_publication() -> None:
    service = _publish(
        history=FakeHistory(RUN),
        consensus=FakeConsensus(CONSENSUS),
        provenance=UnwiredProvenanceGate(),
        citations=FakeCitations(),
        projection=ProjectionAdapter(),
    )
    with pytest.raises(BriefGateUnavailable):
        await service.execute(PublishDecisionBriefRequest(run_id=RunId("run_01J")))


async def test_an_unwired_history_source_blocks_publication() -> None:
    service = _publish(
        history=UnwiredHistorySource(),
        consensus=UnwiredConsensusSource(),
        provenance=UnwiredProvenanceGate(),
        citations=UnwiredCitationResolver(),
        projection=UnwiredProjectionBuilder(),
    )
    with pytest.raises(BriefGateUnavailable):
        await service.execute(PublishDecisionBriefRequest(run_id=RunId("run_01J")))


async def test_a_missing_run_cannot_be_projected() -> None:
    service = _publish(
        history=FakeHistory(None),
        consensus=FakeConsensus(None),
        provenance=FakeProvenance(),
        citations=FakeCitations(),
        projection=ProjectionAdapter(),
    )
    with pytest.raises(BriefSourceIncomplete):
        await service.execute(PublishDecisionBriefRequest(run_id=RunId("run_01J")))


async def test_publication_through_the_ports_freezes_and_saves_the_brief() -> None:
    briefs = InMemoryDecisionBriefRepository()
    events = FakeEvents()
    provenance = FakeProvenance()
    service = _publish(
        history=FakeHistory(RUN),
        consensus=FakeConsensus(CONSENSUS),
        provenance=provenance,
        citations=FakeCitations(),
        projection=ProjectionAdapter(),
        briefs=briefs,
        events=events,
    )
    result = await service.execute(PublishDecisionBriefRequest(run_id=RunId("run_01J")))
    assert result.brief.status is BriefStatus.PUBLISHED
    assert result.brief.version.number == 1
    assert result.brief.disclaimer == DISCLAIMER
    assert provenance.calls == ["run_01J"]
    assert await briefs.get(BriefId("brf_01J")) is result.brief
    assert events.published


def test_the_runtime_binds_the_renderer_and_read_services() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            persistence=Persistence.MEMORY,
        )
    )
    container = app.state.decision_brief
    assert isinstance(container.renderer, JsonBriefRenderer)
    assert container.get_decision_brief is not None


# ── The projection adapter is the real builder the runtime binds (#346) ────────────


def test_the_projection_adapter_builds_a_complete_draft() -> None:
    adapter = BriefProjectionAdapter(ids=UuidFactory(), clock=SystemClock())

    brief = adapter.build(run=RUN, consensus=CONSENSUS, disclaimer=DISCLAIMER)

    assert len(brief.sections) == 8
    assert [section.ordinal for section in brief.sections.values()] == list(range(1, 9))
    assert brief.disclaimer is DISCLAIMER
    assert brief.version.number == 1
    assert brief.version.snapshot_ref == RUN.snapshot_ref
    assert brief.rejected_proposals == RUN.rejected_proposals
    assert brief.status is BriefStatus.DRAFT


def test_the_runtime_binds_the_real_projection_adapter() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            persistence=Persistence.MEMORY,
        )
    )

    service = app.state.decision_brief.publish_decision_brief
    assert isinstance(service.collaborators()[5], BriefProjectionAdapter)
