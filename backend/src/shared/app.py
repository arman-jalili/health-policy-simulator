"""Composition root of the modular monolith (ADR-001) — application shell, not kernel code.

Every context is wired here for the configured persistence family; the in-process outbox relay
runs for PostgreSQL mode. Run with ``uvicorn shared.app:create_app --factory`` or ``hps-api``.

Canonical: .pi/architecture/decisions/ADR-001-architecture-pattern.md
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager, suppress
from typing import TextIO

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from claim_validation.application.commands import VerifyClaimRequest
from claim_validation.composition import build_container as build_claim_validation_container
from claim_validation.interfaces.http.router import router as claim_validation_router
from claim_validation.interfaces.published import to_verdict_view
from consensus_analysis.application.commands import RunClosedRequest as ConsensusRunClosedRequest
from consensus_analysis.application.dto import ModelledEstimate
from consensus_analysis.application.estimators import AssumedEstimator
from consensus_analysis.application.ports import UnitOfWork as ConsensusUnitOfWorkPort
from consensus_analysis.composition import build_container as build_consensus_container
from consensus_analysis.domain.entities import PackageComponent
from consensus_analysis.domain.errors import ConsensusAnalysisUnavailable
from consensus_analysis.domain.repositories import ConsensusRepository
from consensus_analysis.domain.values import BasisKind, ScenarioId
from consensus_analysis.domain.values import RunId as ConsensusRunId
from consensus_analysis.infrastructure.acl import IllustrativeExampleCatalog
from consensus_analysis.infrastructure.comparison import LexicographicRanker
from consensus_analysis.infrastructure.negotiation_sources import (
    runtime_mandate,
    runtime_powers,
    runtime_run_log,
)
from consensus_analysis.infrastructure.projection import LogFoldingRebuilder
from consensus_analysis.infrastructure.repository.memory import (
    InMemoryConsensusRepository,
    InMemoryEventPublisher,
    InMemoryPackageRepository,
    InMemoryScenarioRepository,
)
from consensus_analysis.infrastructure.repository.memory import (
    NoopUnitOfWork as ConsensusUnitOfWork,
)
from consensus_analysis.infrastructure.repository.sqlalchemy import (
    SqlAlchemyConsensusRepository,
)
from consensus_analysis.interfaces.http.router import router as consensus_analysis_router
from decision_brief.application.ports import EventPublisher as BriefEventPublisher
from decision_brief.application.ports import UnitOfWork as BriefUnitOfWork
from decision_brief.composition import build_container as build_decision_brief_container
from decision_brief.domain.repositories import DecisionBriefRepository
from decision_brief.domain.values import BRIEF_PROMPT_VERSION, SimulationDisclaimer
from decision_brief.infrastructure.acl import (
    ConsensusViewAcl,
    EvidenceCorpusCitationResolver,
    GovernanceProvenanceGate,
    NegotiationHistoryAcl,
)
from decision_brief.infrastructure.projection import BriefProjectionAdapter
from decision_brief.infrastructure.repository.memory import InMemoryDecisionBriefRepository
from decision_brief.infrastructure.repository.sqlalchemy import (
    SqlAlchemyDecisionBriefRepository,
)
from decision_brief.infrastructure.runtime import (
    LoggingEventPublisher,
    SharedOutboxEventPublisher,
    UuidFactory,
)
from decision_brief.interfaces.http.router import router as decision_brief_router
from decision_brief.interfaces.renderer import JsonBriefRenderer
from evidence_corpus.composition import build_container
from evidence_corpus.domain.values import ClaimType as CorpusClaimType
from evidence_corpus.interfaces.http.router import router as evidence_corpus_router
from evidence_retrieval.application.commands import AssembleEvidencePackRequest
from evidence_retrieval.composition import build_container as build_retrieval_container
from evidence_retrieval.domain.values import ClaimText
from evidence_retrieval.interfaces.http.router import router as evidence_retrieval_router
from governance_compliance.composition import build_container as build_governance_container
from governance_compliance.infrastructure.allowlist import StaticAllowlistSource, from_published
from governance_compliance.infrastructure.facts import NegotiationProvenanceFacts
from governance_compliance.infrastructure.figures import ClaimValidationFigureVerdicts
from governance_compliance.interfaces.http.router import router as governance_compliance_router
from identity_access.composition import build_identity_access_container
from identity_access.interfaces.http.router import router as identity_access_router
from negotiation_session.application.mappers import claim_is_admissible
from negotiation_session.composition import build_container as build_negotiation_container
from negotiation_session.infrastructure.acl import (
    GovernanceGuardAdapter,
    PositionProvenanceAcl,
)
from negotiation_session.infrastructure.progress import InMemoryProgressBroker
from negotiation_session.infrastructure.upstream import (
    ClaimVerdicts,
    RequiredInvocationLookup,
    RetrievalEvidencePacks,
    StakeholderProfiles,
)
from negotiation_session.interfaces.http.router import router as negotiation_session_router
from shared.clock import SystemClock
from shared.config import Settings, get_settings
from shared.db import Database
from shared.db import UnitOfWork as DbUnitOfWork
from shared.enums import Persistence
from shared.http.errors import register_error_handlers
from shared.http.health import router as health_router
from shared.http.metrics import router as metrics_router
from shared.http.middleware import RequestContextMiddleware
from shared.log_setup import configure_logging, get_logger
from shared.outbox import OutboxEvent
from shared.relay import WILDCARD, OutboxRelay
from simulation_orchestration.composition import build_container as build_simulation_container
from simulation_orchestration.infrastructure.negotiation_session import (
    EvidenceBriefing,
    NegotiationSessionGateway,
)
from simulation_orchestration.interfaces.http.router import (
    router as simulation_orchestration_router,
)
from stakeholder_model.composition import build_container as build_stakeholder_container
from stakeholder_model.interfaces.http.router import router as stakeholder_model_router

logger = get_logger(__name__)


def create_app(settings: Settings | None = None, *, log_stream: TextIO | None = None) -> FastAPI:
    """Build the ASGI application. Configuration errors abort here, before serving."""
    app_settings = settings or get_settings()
    configure_logging(app_settings, stream=log_stream)
    database = Database(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        relay_task: asyncio.Task[None] | None = None
        worker_task: asyncio.Task[None] | None = None
        worker_stop = asyncio.Event()
        logger.info(
            "service_starting",
            env=str(app_settings.env),
            auth_mode=str(app_settings.auth_mode),
            version=app_settings.version,
        )
        if app_settings.is_demo:
            logger.warning(
                "demo_auth_mode_enabled",
                detail="anonymous reads and runs:write are allowed from localhost only"
                if not app_settings.auth_demo_trusted_cidrs
                else "anonymous access is allowed from loopback and AUTH_DEMO_TRUSTED_CIDRS",
                trusted_cidrs=",".join(app_settings.auth_demo_trusted_cidrs) or "loopback",
            )
        try:
            await database.ping()
        except Exception as error:
            logger.warning("database_unreachable_at_startup", error=str(error))
        if app_settings.persistence is Persistence.POSTGRES:
            relay = OutboxRelay(database.session_factory, poll_interval_s=5.0)
            relay.subscribe(WILDCARD, _log_dispatched_event)
            relay_task = asyncio.create_task(relay.run(), name="outbox-relay")
        worker = app.state.simulation_orchestration.worker
        try:
            resumable = await worker.recover()
            logger.info("simulation_worker_boot_recovery", resumable=resumable)
        except Exception as error:
            logger.warning("simulation_worker_recovery_failed", error=str(error))
        worker_task = asyncio.create_task(
            worker.run_supervised(worker_stop),
            name="simulation-worker",
        )
        app.state.simulation_worker_task = worker_task
        try:
            yield
        finally:
            worker_stop.set()
            if worker_task is not None:
                with suppress(asyncio.CancelledError, TimeoutError):
                    await asyncio.wait_for(worker_task, timeout=2.0)
            if relay_task is not None:
                relay_task.cancel()
                with suppress(asyncio.CancelledError):
                    await relay_task
            await database.dispose()
            logger.info("service_stopped")

    app = FastAPI(
        title=app_settings.service_name,
        version=app_settings.version,
        summary="Institutional negotiation simulator for Austrian healthcare policy",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.db = database
    app.state.corpus = build_container(app_settings, database)
    app.state.evidence_retrieval = build_retrieval_container(
        app_settings, database, corpus=app.state.corpus
    )
    app.state.identity_access = build_identity_access_container(app_settings, database)
    app.state.stakeholder_model = build_stakeholder_container(app_settings, database)
    app.state.claim_validation = build_claim_validation_container(app_settings, database)
    app.state.governance_compliance = build_governance_container(
        app_settings,
        database,
        allowlist_source=StaticAllowlistSource(
            from_published(app.state.stakeholder_model.allowlist)
        ),
        figure_verdicts=ClaimValidationFigureVerdicts(app.state.claim_validation.claims),
    )
    app.state.negotiation_progress = InMemoryProgressBroker()
    stakeholder_profiles = StakeholderProfiles(app.state.stakeholder_model)
    app.state.negotiation_session = build_negotiation_container(
        app_settings,
        database,
        evidence=RetrievalEvidencePacks(app.state.evidence_retrieval),
        stakeholders=stakeholder_profiles,
        claims=ClaimVerdicts(app.state.claim_validation),
        governance=GovernanceGuardAdapter(
            app.state.governance_compliance.enforce_institution_only_output
        ),
        invocations=RequiredInvocationLookup(),
        progress=app.state.negotiation_progress,
    )
    close_uow = app.state.negotiation_session.bind_position_provenance(
        PositionProvenanceAcl(app.state.governance_compliance.disclose_position_provenance)
    )
    if app_settings.persistence is Persistence.POSTGRES:
        app.state.governance_compliance.bind_unit_of_work(close_uow)

    async def _evidence_pack_for(claim: str) -> EvidenceBriefing:
        existing = await app.state.evidence_retrieval.packs.latest_for_claim(ClaimText(claim))
        if existing is not None and existing.candidates:
            return EvidenceBriefing(
                pack_id=str(existing.id),
                passage_ids=tuple(str(item.passage_id) for item in existing.candidates),
            )
        snapshot = await app.state.corpus.snapshots.latest()
        if snapshot is None:
            raise RuntimeError(
                "no corpus snapshot exists; seed or pin the corpus before simulating"
            )
        assembled = await app.state.evidence_retrieval.assemble_pack.execute(
            AssembleEvidencePackRequest(
                claim=claim,
                claim_type=CorpusClaimType.QUALITATIVE,
                snapshot_id=snapshot.id,
            )
        )
        if assembled.candidates:
            return EvidenceBriefing(
                pack_id=str(assembled.pack_id),
                passage_ids=tuple(str(item.passage_id) for item in assembled.candidates),
            )
        # A demo question need not share words with a passage; the seeded pack keeps the turn
        # evidenced rather than submitting a position that cites nothing.
        seeded = await app.state.evidence_retrieval.packs.latest_for_claim(
            ClaimText("Die Kassenstellen sollen ausgebaut werden.")
        )
        if seeded is not None and seeded.candidates:
            return EvidenceBriefing(
                pack_id=str(seeded.id),
                passage_ids=tuple(str(item.passage_id) for item in seeded.candidates),
            )
        return EvidenceBriefing(pack_id=str(assembled.pack_id))

    async def _claim_admissible(text: str) -> bool:
        """Ask ClaimValidation whether a model-written claim may enter an argument (ADR-012).

        The negotiation domain refuses inadmissible claims outright; the orchestrated path therefore
        filters first and lets the remaining text stand as narrative.
        """
        result = await app.state.claim_validation.verify_claim.execute(
            VerifyClaimRequest(text=text)
        )
        return claim_is_admissible(
            to_verdict_view(
                claim_id=result.claim_id,
                verdict=result.verdict.value,
                claim_type=result.claim_type.value,
                sources=tuple(result.sources),
                delta=result.delta,
            )
        )

    app.state.simulation_orchestration = build_simulation_container(
        app_settings,
        database,
        negotiation=NegotiationSessionGateway(
            claim_admissible=_claim_admissible,
            runs=app.state.negotiation_session.get_simulation_run,
            open_round=app.state.negotiation_session.open_round,
            submit_position=app.state.negotiation_session.submit_initial_position,
            take_turn=app.state.negotiation_session.take_negotiation_turn,
            close_round=app.state.negotiation_session.close_round,
            evidence_pack_for=_evidence_pack_for,
        ),
    )
    if app_settings.persistence is Persistence.POSTGRES:
        consensus_repository: ConsensusRepository = SqlAlchemyConsensusRepository(
            database.session_factory
        )
        consensus_uow: ConsensusUnitOfWorkPort = DbUnitOfWork(database.session_factory)
    else:
        consensus_repository = InMemoryConsensusRepository()
        consensus_uow = ConsensusUnitOfWork()
    app.state.consensus_analysis = build_consensus_container(
        app_settings,
        database,
        consensus=consensus_repository,
        packages=InMemoryPackageRepository(),
        scenarios=InMemoryScenarioRepository(),
        log=runtime_run_log(app.state.negotiation_session.get_simulation_run),
        powers=runtime_powers(stakeholder_profiles),
        mandate=runtime_mandate(app.state.negotiation_session.get_simulation_run),
        estimation={BasisKind.ASSUMED: AssumedEstimator()},
        catalogue=IllustrativeExampleCatalog(examples=()),
        components=_EmptyComponentCatalogue(),
        llm=_UnavailableLlm(),
        rebuilder=LogFoldingRebuilder(ids=_ids),
        ranker=LexicographicRanker(),
        events=InMemoryEventPublisher(),
        clock=SystemClock(),
        ids=_ids,
        uow=consensus_uow,
    )

    async def _derive_on_run_closed(run: object) -> None:
        run_id = getattr(run, "id", None)
        if run_id is None:
            return
        try:
            await app.state.consensus_analysis.handle_run_closed.execute(
                ConsensusRunClosedRequest(run_id=ConsensusRunId(str(run_id)))
            )
        except Exception as error:  # derivation is fail-closed; never mask the close itself
            logger.warning("consensus_run_closed_derivation_failed", error=str(error))

    app.state.negotiation_session.subscribe_run_closed(_derive_on_run_closed)
    app.state.governance_compliance.disclose_position_provenance._facts = (
        NegotiationProvenanceFacts(
            runs=app.state.negotiation_session.get_simulation_run,
            model=app_settings.simulation_model_id,
            prompt_version="bootstrap-turn@1",
        )
    )
    app.state.governance_provenance = "wired"
    app.state.governance_provenance_producer = "close_round"
    if app_settings.persistence is Persistence.POSTGRES:
        brief_repository: DecisionBriefRepository = SqlAlchemyDecisionBriefRepository(
            database.session_factory
        )
        brief_events: BriefEventPublisher = SharedOutboxEventPublisher(database.session_factory)
        brief_uow: BriefUnitOfWork = DbUnitOfWork(database.session_factory)
    else:
        brief_repository = InMemoryDecisionBriefRepository()
        brief_events = LoggingEventPublisher()
        brief_uow = ConsensusUnitOfWork()
    app.state.decision_brief = build_decision_brief_container(
        app_settings,
        database,
        briefs=brief_repository,
        history=NegotiationHistoryAcl(runs=app.state.negotiation_session.get_simulation_run),
        consensus=ConsensusViewAcl(consensus=app.state.consensus_analysis),
        citations=EvidenceCorpusCitationResolver(app.state.corpus.resolve_passage),
        provenance=GovernanceProvenanceGate(
            runs=app.state.negotiation_session.get_simulation_run,
            provenance=app.state.governance_compliance.get_position_provenance,
        ),
        projection=BriefProjectionAdapter(ids=UuidFactory(), clock=SystemClock()),
        disclaimer=SimulationDisclaimer.canonical(
            model_reference=app_settings.simulation_model_id,
            prompt_version=BRIEF_PROMPT_VERSION,
        ),
        events=brief_events,
        clock=SystemClock(),
        ids=UuidFactory(),
        uow=brief_uow,
        renderer=JsonBriefRenderer(),
    )

    if app_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key", "X-Request-ID"],
            expose_headers=["X-Request-ID", "X-Trace-Id"],
        )

    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(evidence_corpus_router)
    app.include_router(evidence_retrieval_router)
    app.include_router(identity_access_router)
    app.include_router(stakeholder_model_router)
    app.include_router(claim_validation_router)
    app.include_router(simulation_orchestration_router)
    app.include_router(governance_compliance_router)
    app.include_router(consensus_analysis_router)
    app.include_router(negotiation_session_router)
    app.include_router(decision_brief_router)
    return app


_ids = UuidFactory()
"""Every process uses prefixed ULIDs, so projection ids never collide across restarts."""


class _EmptyComponentCatalogue:
    """No component catalogue is published yet, so the package cannot assemble itself."""

    async def components(self, run_id: ConsensusRunId) -> Sequence[PackageComponent]:
        raise ConsensusAnalysisUnavailable(
            "accepted components are not published per run yet; a package cannot be assembled "
            "around parts nobody accepted"
        )


class _UnavailableLlm:
    """The metered model client is not reachable from this context yet (ADR-006)."""

    async def estimate(
        self, *, scenario_id: ScenarioId, field: str, context: str
    ) -> ModelledEstimate:
        raise ConsensusAnalysisUnavailable(
            "no metered model client is configured for consensus-analysis; modelled figures "
            "cannot be produced without one"
        )


async def _log_dispatched_event(event: OutboxEvent) -> None:
    """Phase 1 in-process subscriber: make relayed events observable until consumers exist."""
    logger.info(
        "domain_event_dispatched",
        event_name=event.event_name,
        event_id=event.event_id,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
    )


def main() -> None:
    """Console entrypoint (``hps-api``)."""
    settings = get_settings()
    uvicorn.run(
        "shared.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":  # pragma: no cover - process entry
    main()
