"""Use-case request DTOs of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (API Endpoints)

These are the only inputs an application service accepts. ``RunClosedRequest`` is the event-driven
entry point: the wiring issue subscribes it to the run-closed notice so a closed run produces
consensus rows with no explicit API call (AC 12).
"""

from __future__ import annotations

from dataclasses import dataclass

from consensus_analysis.domain.values import (
    BaselineRef,
    ComponentId,
    Horizon,
    PackageId,
    RunId,
    ScenarioAssumption,
    TopicRef,
)


@dataclass(frozen=True, slots=True)
class DeriveConsensusRequest:
    """Derive the records of one closed run; ``topics`` narrows an otherwise full derivation."""

    run_id: RunId
    topics: tuple[TopicRef, ...] = ()


@dataclass(frozen=True, slots=True)
class GetConsensusRequest:
    run_id: RunId


@dataclass(frozen=True, slots=True)
class ListUnresolvedConflictsRequest:
    run_id: RunId


@dataclass(frozen=True, slots=True)
class ComposeCompromisePackageRequest:
    run_id: RunId
    component_ids: tuple[ComponentId, ...] = ()
    rejected_ids: tuple[ComponentId, ...] = ()


@dataclass(frozen=True, slots=True)
class ListPackagesRequest:
    run_id: RunId


@dataclass(frozen=True, slots=True)
class AssessImpactRequest:
    package_id: PackageId
    baseline: BaselineRef
    horizon: Horizon
    assumptions: tuple[ScenarioAssumption, ...] = ()


@dataclass(frozen=True, slots=True)
class CompareScenariosRequest:
    package_id: PackageId


@dataclass(frozen=True, slots=True)
class RebuildProjectionsRequest:
    """Operator command: replay the run log and prove the rows are reproducible (AC 4)."""

    run_id: RunId
    verify_only: bool = False


@dataclass(frozen=True, slots=True)
class RunClosedRequest:
    """Notice published when a simulation run closes; the subscriber derives from it (AC 12)."""

    run_id: RunId
    condition: str = ""
    rounds: int = 0
    final_phase: str = ""
