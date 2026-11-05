"""Domain-owned repository and open-host ports of StakeholderModel (ADR-001, ADR-003).

Canonical: .pi/architecture/modules/stakeholder-model.md

Repository protocols live with the domain so application services never depend on SQLAlchemy. The
``CorpusEvidencePort`` is the published EvidenceCorpus language; no corpus table is read here.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from evidence_corpus.domain.published import PassageView
from stakeholder_model.domain.agent_binding import AgentBinding
from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import InstitutionIdentity, RunId, StakeholderId


@runtime_checkable
class StakeholderRepository(Protocol):
    """Persistence port for the Stakeholder aggregate (one aggregate per transaction)."""

    async def get(self, stakeholder_id: StakeholderId) -> Stakeholder | None: ...

    async def save(self, stakeholder: Stakeholder) -> None: ...

    async def all_registered(self) -> list[Stakeholder]: ...


@runtime_checkable
class AgentBindingRepository(Protocol):
    """Persistence port for immutable AgentBinding records."""

    async def get_for_run(
        self, run_id: RunId, stakeholder_id: StakeholderId
    ) -> AgentBinding | None: ...

    async def save(self, binding: AgentBinding) -> None: ...


@runtime_checkable
class CorpusEvidencePort(Protocol):
    """Published EvidenceCorpus port used to ground historical positions."""

    async def passages_about(self, identity: InstitutionIdentity) -> list[PassageView]: ...
