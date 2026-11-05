"""Views published to other contexts (contract frozen, issue #205)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from simulation_orchestration.application.values import JobStatus, RunId


@dataclass(frozen=True, slots=True)
class InvocationProvenanceView:
    """Link from an argument to its model call; carries no prompt body."""

    invocation_id: str
    run_id: RunId
    model: str
    prompt_name: str
    prompt_version: int
    cost_estimate: Decimal


@dataclass(frozen=True, slots=True)
class JobStatusView:
    job_id: str
    run_id: RunId
    status: JobStatus
    rounds_completed: int
    last_sequence: int
