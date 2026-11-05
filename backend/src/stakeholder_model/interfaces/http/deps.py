"""FastAPI dependencies and the frozen service container of StakeholderModel.

Canonical: .pi/architecture/modules/stakeholder-model.md

The composition root binds ``app.state.stakeholder_model`` in the wiring issue. Keeping the
container shape here means the router depends on ports, never on concrete adapters.
"""

from __future__ import annotations

from typing import Protocol, cast

from fastapi import Request

from stakeholder_model.application import commands, dto, ports, services


class StakeholderModelContainer(Protocol):
    """Services and transaction scope exposed by the composition root."""

    register_stakeholder: services.RegisterStakeholder
    update_profile: services.UpdateStakeholderProfile
    cite_power_source: services.CitePowerSource
    record_position: services.RecordHistoricalPosition
    select_stakeholders: services.SelectRelevantStakeholders
    bind_persona: services.BindAgentPersona
    get_profile: services.GetStakeholderProfile
    list_stakeholders: services.ListStakeholders
    list_positions: services.ListHistoricalPositions
    load_personas: services.LoadPersonaCards
    publish_allowlist: services.PublishInstitutionalAllowlist
    transaction: ports.UnitOfWork


def get_container(request: Request) -> StakeholderModelContainer:
    """Return the wired StakeholderModel container of the running application."""
    return cast(StakeholderModelContainer, request.app.state.stakeholder_model)


_CONTRACT_TYPES: tuple[type[object], ...] = (
    commands.RegisterStakeholderRequest,
    dto.StakeholderSummaryResult,
)
"""Referenced by the contract checker; keeps request/result shapes discoverable from interfaces."""
