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
from simulation_orchestration.application.ports import (
    LLMClient,
    LlmProviderControl,
    NegotiationGateway,
    WorkerLoop,
)
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
    GetLlmProvider,
    PauseOrResumeSimulation,
    RecordAgentInvocation,
    RegisterPromptTemplate,
    ResolvePromptTemplate,
    RunSimulationJob,
    SelectLlmProvider,
    StreamSimulationProgress,
)
from simulation_orchestration.application.values import ModelPrice
from simulation_orchestration.infrastructure.graph import SequentialWorkflowGraph
from simulation_orchestration.infrastructure.llm import (
    HttpLlmClient,
    ScriptedLLMClient,
    SwitchableLlmClient,
)
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
    select_llm_provider: SelectLlmProvider
    get_llm_provider: GetLlmProvider
    llm_control: LlmProviderControl
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
    # Both variants live in one facade so a demo can flip between the live model and the
    # scripted stand-in without a restart. The live variant needs a key and a base URL.
    # The stand-in always reports the canonical scripted model id, independent of the live model
    # configured for the demo (the price table keys on it and the UI shows it verbatim).
    scripted_model = "scripted-local"
    variants: dict[str, LLMClient] = {"scripted": ScriptedLLMClient(scripted_model)}
    if settings.llm_base_url is not None and settings.llm_api_key is not None:
        live_name = provider if provider != "scripted" else "openai-compatible"
        variants[live_name] = HttpLlmClient(
            model_id=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout_s=settings.llm_timeout_s,
            max_retries=settings.llm_max_retries,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
            json_mode=settings.llm_json_mode,
            reasoning_effort=settings.llm_reasoning_effort,
        )
    if provider != "scripted" and provider not in variants:
        raise ValueError("LLM_BASE_URL and LLM_API_KEY are required for a real provider")
    active_variant = provider if provider in variants else "scripted"
    llm = SwitchableLlmClient(variants, active=active_variant)
    price_entries: dict[str, ModelPrice] = {
        model_id: ModelPrice(
            model_id=model_id,
            input_per_1k=Decimal(str(settings.simulation_input_price_per_1k)),
            output_per_1k=Decimal(str(settings.simulation_output_price_per_1k)),
        )
    }
    # The scripted variant reports its own model id and stays free when a demo switches to it.
    # Only add it when it is a different model, otherwise it would overwrite configured prices.
    if scripted_model != model_id:
        price_entries[scripted_model] = ModelPrice(
            model_id=scripted_model,
            input_per_1k=Decimal("0"),
            output_per_1k=Decimal("0"),
        )
    prices = StaticPriceTable(price_entries)
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
                # Read the facade, not the boot setting: the demo may switch at runtime.
                scripted=lambda: llm.active() == "scripted",
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
            invocations=invocations, model=llm.active_model(), provider=provider
        ),
        register_prompt_template=RegisterPromptTemplate(
            registry=registry, versioning=PromptVersioning(), clock=clock
        ),
        resolve_prompt_template=ResolvePromptTemplate(registry=registry),
        worker=BackgroundWorker(run_job),
        select_llm_provider=SelectLlmProvider(control=llm),
        get_llm_provider=GetLlmProvider(control=llm),
        llm_control=llm,
        model=model_id,
        provider=provider,
    )
