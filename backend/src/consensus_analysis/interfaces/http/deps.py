"""HTTP container dependency (contract frozen, issue #305).

The composition root binds ``app.state.consensus_analysis`` in the wiring issue. Keeping the
container shape here means the router depends on the frozen service surface, never on an adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from consensus_analysis.application.services import (
    AssessImpact,
    CompareScenarios,
    ComposeCompromisePackage,
    DeriveConsensus,
    GetConsensus,
    HandleRunClosed,
    ListPackages,
    ListUnresolvedConflicts,
    RebuildProjections,
)


class ConsensusAnalysisContainer(Protocol):
    """Services exposed by the composition root."""

    derive_consensus: DeriveConsensus
    get_consensus: GetConsensus
    list_unresolved_conflicts: ListUnresolvedConflicts
    compose_compromise_package: ComposeCompromisePackage
    list_packages: ListPackages
    assess_impact: AssessImpact
    compare_scenarios: CompareScenarios
    rebuild_projections: RebuildProjections
    handle_run_closed: HandleRunClosed


@dataclass(frozen=True, slots=True)
class ContainerView:
    container: ConsensusAnalysisContainer


def get_container(request: Request) -> ConsensusAnalysisContainer:
    container = getattr(request.app.state, "consensus_analysis", None)
    if container is None:
        raise RuntimeError("consensus_analysis container is not mounted")
    return container  # type: ignore[no-any-return]
