"""Frozen composition factory (contract frozen, issue #205).

The factory is intentionally not called by ``shared/app.py`` until issue #216. It names every
dependency the runtime must provide, including the ACL to NegotiationSession.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.config import Settings
from shared.db import Database
from simulation_orchestration.application.ports import NegotiationGateway
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


def build_container(
    settings: Settings, database: Database, negotiation: NegotiationGateway
) -> SimulationOrchestrationContainer:
    raise NotImplementedError("simulation-orchestration composition is implemented by issue #216")
