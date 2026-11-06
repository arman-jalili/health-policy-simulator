"""Views published to other contexts (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Dependencies)

ConsensusAnalysis, DecisionBrief, GovernanceCompliance and SimulationOrchestration consume
these read shapes and the published events in ``domain/events.py``. They contain ids and facts,
never repository, ORM, retrieval or vector types.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunSnapshotView:
    run_id: str
    phase: str
    round: int
    round_cap: int
    closed: bool
    bound_stakeholder_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PositionView:
    position_id: str
    stakeholder_id: str
    topic: str
    stance: str
    evidence_ids: tuple[str, ...]
    supersedes: str | None = None


@dataclass(frozen=True, slots=True)
class ArgumentView:
    argument_id: str
    round: int
    stakeholder_id: str
    topic: str
    stance: str
    evidence_ids: tuple[str, ...]
    unsupported: bool
    invocation_id: str | None = None


@dataclass(frozen=True, slots=True)
class CoalitionView:
    coalition_id: str
    topic: str
    member_ids: tuple[str, ...]
    proposal_summary: str


@dataclass(frozen=True, slots=True)
class RunClosedView:
    run_id: str
    condition: str
    rounds: int
    final_phase: str
