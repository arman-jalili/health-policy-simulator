"""In-memory repository adapters for stakeholder-model wiring and tests.

Canonical: .pi/architecture/modules/stakeholder-model.md

The in-memory family keeps the composition root honest for ``PERSISTENCE=memory`` and for the
contract/wiring tests. PostgreSQL persistence is added by the runtime-integration issue.
"""

from __future__ import annotations

from stakeholder_model.domain.agent_binding import AgentBinding
from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import RunId, StakeholderId


class InMemoryStakeholderRepository:
    """Registry preserving insertion order and aggregate identity."""

    def __init__(self, stakeholders: list[Stakeholder] | None = None) -> None:
        self._stakeholders = {stakeholder.id: stakeholder for stakeholder in (stakeholders or [])}

    async def get(self, stakeholder_id: StakeholderId) -> Stakeholder | None:
        return self._stakeholders.get(stakeholder_id)

    async def save(self, stakeholder: Stakeholder) -> None:
        self._stakeholders[stakeholder.id] = stakeholder

    async def all_registered(self) -> list[Stakeholder]:
        return list(self._stakeholders.values())


class InMemoryAgentBindingRepository:
    """Immutable binding storage keyed by run + stakeholder."""

    def __init__(self) -> None:
        self._bindings: dict[tuple[RunId, StakeholderId], AgentBinding] = {}

    async def get_for_run(
        self, run_id: RunId, stakeholder_id: StakeholderId
    ) -> AgentBinding | None:
        return self._bindings.get((run_id, stakeholder_id))

    async def save(self, binding: AgentBinding) -> None:
        existing = self._bindings.get((binding.run_id, binding.stakeholder_id))
        if existing is not None and existing != binding:
            raise ValueError("agent binding is immutable for the run")
        self._bindings[(binding.run_id, binding.stakeholder_id)] = binding
