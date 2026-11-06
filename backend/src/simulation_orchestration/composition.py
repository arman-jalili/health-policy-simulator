"""Composition factory (implemented by issue #216)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared.clock import SystemClock
from shared.config import Settings
from shared.db import Database
from shared.db import UnitOfWork as DbUnitOfWork
from shared.enums import Persistence
from shared.log_setup import get_logger
from simulation_orchestration.application.errors import UnknownModel
from simulation_orchestration.application.ports import LLMClient, NegotiationGateway, WorkerLoop
from simulation_orchestration.application.repositories import (
    InvocationStore,
    JobStore,
    ProgressStore,
    PromptRegistry,
)
from simulation_orchestration.application.rules import (
    BudgetGuard,
    CheckpointPolicy,
    PromptVersioning,
)
from simulation_orchestration.application.services import (
    CollectUsageReport,
    GetJob,
    PauseOrResumeSimulation,
    RecordAgentInvocation,
    RegisterPromptTemplate,
    ResolvePromptTemplate,
    RunSimulationJob,
    StreamSimulationProgress,
)
from simulation_orchestration.application.values import ModelPrice
from simulation_orchestration.infrastructure.graph import SequentialWorkflowGraph
from simulation_orchestration.infrastructure.llm import HttpLlmClient, ScriptedLLMClient
from simulation_orchestration.infrastructure.memory import (
    InMemoryInvocationStore,
    InMemoryJobStore,
    InMemoryProgressStore,
    InMemoryPromptRegistry,
)
from simulation_orchestration.infrastructure.negotiation_nodes import (
    NegotiationPrepareNode,
    NegotiationTurnNode,
)
from simulation_orchestration.infrastructure.pricing import StaticPriceTable
from simulation_orchestration.infrastructure.repository.sqlalchemy import (
    SqlAlchemyInvocationStore,
    SqlAlchemyJobStore,
    SqlAlchemyProgressStore,
    SqlAlchemyPromptRegistry,
)
from simulation_orchestration.infrastructure.worker import BackgroundWorker

_SUPPORTED_MODELS = frozenset({"scripted-local"})
logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SimulationOrchestrationContainer:
    run_simulation_job: RunSimulationJob
    stream_simulation_progress: StreamSimulationProgress
    pause_or_resume_simulation: PauseOrResumeSimulation
    record_agent_invocation: RecordAgentInvocation
    get_job: GetJob
    collect_usage_report: CollectUsageReport
    register_prompt_template: RegisterPromptTemplate
    resolve_prompt_template: ResolvePromptTemplate
    worker: WorkerLoop
    model: str = ""
    provider: str = "scripted"


def build_container(
    settings: Settings,
    database: Database,
    negotiation: NegotiationGateway | None = None,
) -> SimulationOrchestrationContainer:
    if negotiation is None:
        raise ValueError(
            "SimulationOrchestration requires a real NegotiationGateway; "
            "NoopNegotiationGateway is test-only and must not be a production default"
        )
    provider = settings.llm_provider.strip().lower()
    model_id = settings.simulation_model_id if provider == "scripted" else settings.llm_model
    if provider == "scripted" and model_id not in _SUPPORTED_MODELS:
        raise UnknownModel(f"no price entry for configured model {model_id!r}")
    clock = SystemClock()
    if settings.persistence is Persistence.POSTGRES:
        jobs: JobStore = SqlAlchemyJobStore(database.session_factory)
        invocations: InvocationStore = SqlAlchemyInvocationStore(database.session_factory)
        progress: ProgressStore = SqlAlchemyProgressStore(database.session_factory)
        registry: PromptRegistry = SqlAlchemyPromptRegistry(database.session_factory)
    else:
        jobs = InMemoryJobStore()
        invocations = InMemoryInvocationStore()
        progress = InMemoryProgressStore()
        registry = InMemoryPromptRegistry()
    if (
        settings.simulation_input_price_per_1k == 0
        and settings.simulation_output_price_per_1k == 0
        and not settings.simulation_allow_zero_price
    ):
        raise ValueError("simulation model prices are zero; set SIMULATION_ALLOW_ZERO_PRICE=true")
    llm: LLMClient
    if provider == "scripted":
        llm = ScriptedLLMClient(model_id)
    else:
        if settings.llm_base_url is None or settings.llm_api_key is None:
            raise ValueError("LLM_BASE_URL and LLM_API_KEY are required for a real provider")
        llm = HttpLlmClient(
            model_id=model_id,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
        )
    prices = StaticPriceTable(
        {
            model_id: ModelPrice(
                model_id=model_id,
                input_per_1k=Decimal(str(settings.simulation_input_price_per_1k)),
                output_per_1k=Decimal(str(settings.simulation_output_price_per_1k)),
            )
        }
    )
    record_agent_invocation = RecordAgentInvocation(
        invocations=invocations, prices=prices, clock=clock
    )
    graph = SequentialWorkflowGraph(
        [
            NegotiationPrepareNode(negotiation=negotiation),
            NegotiationTurnNode(
                recorder=record_agent_invocation,
                negotiation=negotiation,
                llm=llm,
                model=model_id,
                synthetic=(
                    provider == "scripted"
                    and settings.simulation_input_price_per_1k == 0
                    and settings.simulation_output_price_per_1k == 0
                ),
                scripted=provider == "scripted",
            ),
        ]
    )
    uow = DbUnitOfWork(database.session_factory)
    run_job = RunSimulationJob(
        graph=graph,
        negotiation=negotiation,
        jobs=jobs,
        invocations=invocations,
        progress=progress,
        budget_guard=BudgetGuard(),
        checkpoint_policy=CheckpointPolicy(),
        clock=clock,
        uow=uow,
    )
    logger.info(
        "simulation_orchestration_wired",
        persistence=settings.persistence.value,
        model=model_id,
        stores="postgresql" if settings.persistence is Persistence.POSTGRES else "memory",
    )
    return SimulationOrchestrationContainer(
        run_simulation_job=run_job,
        stream_simulation_progress=StreamSimulationProgress(
            progress=progress,
            idle_timeout_s=settings.simulation_stream_idle_s,
            heartbeat_s=settings.simulation_stream_heartbeat_s,
        ),
        pause_or_resume_simulation=PauseOrResumeSimulation(
            jobs=jobs,
            progress=progress,
            clock=clock,
            uow=uow,
        ),
        record_agent_invocation=record_agent_invocation,
        get_job=GetJob(jobs=jobs, progress=progress),
        collect_usage_report=CollectUsageReport(
            invocations=invocations, model=model_id, provider=provider
        ),
        register_prompt_template=RegisterPromptTemplate(
            registry=registry, versioning=PromptVersioning(), clock=clock
        ),
        resolve_prompt_template=ResolvePromptTemplate(registry=registry),
        worker=BackgroundWorker(run_job),
        model=model_id,
        provider=provider,
    )
