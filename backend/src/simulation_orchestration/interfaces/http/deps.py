"""HTTP container dependency (contract frozen, issue #205)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from simulation_orchestration.application.services import (
    CollectUsageReport,
    GetJob,
    PauseOrResumeSimulation,
    RunSimulationJob,
    StreamSimulationProgress,
)


class SimulationOrchestrationContainer(Protocol):
    run_simulation_job: RunSimulationJob
    stream_simulation_progress: StreamSimulationProgress
    pause_or_resume_simulation: PauseOrResumeSimulation
    get_job: GetJob
    collect_usage_report: CollectUsageReport


@dataclass(frozen=True, slots=True)
class ContainerView:
    container: SimulationOrchestrationContainer


def get_container(request: Request) -> SimulationOrchestrationContainer:
    container = getattr(request.app.state, "simulation_orchestration", None)
    if container is None:
        raise RuntimeError("simulation_orchestration container is not mounted")
    return container  # type: ignore[no-any-return]
