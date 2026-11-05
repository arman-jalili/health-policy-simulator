"""Repository implementation boundary (contract frozen, issue #205).

The protocols are declared in ``application/repositories.py`` so application code never imports
infrastructure. This module is the import point for adapters and the proofing check.
"""

from __future__ import annotations

from simulation_orchestration.application.repositories import (
    InvocationStore,
    JobStore,
    ProgressStore,
    PromptRegistry,
)

__all__ = ["InvocationStore", "JobStore", "ProgressStore", "PromptRegistry"]
