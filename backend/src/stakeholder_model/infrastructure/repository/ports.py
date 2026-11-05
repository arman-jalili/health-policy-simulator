"""Repository/DAO ports as seen by infrastructure adapters.

Canonical: .pi/architecture/modules/stakeholder-model.md

The authoritative protocols live in ``domain/repositories.py`` so application code depends inward.
This module re-exports them for adapter authors and keeps the infrastructure/repository package
discoverable without duplicating the contract.
"""

from __future__ import annotations

from stakeholder_model.domain.repositories import (
    AgentBindingRepository,
    CorpusEvidencePort,
    StakeholderRepository,
)

__all__ = ["AgentBindingRepository", "CorpusEvidencePort", "StakeholderRepository"]
