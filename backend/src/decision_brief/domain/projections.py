"""Frozen domain projections consumed by the projection builder (contract frozen, issue #331).

These are DecisionBrief's own read model, assembled by an ACL from the published views of
NegotiationSession (``RunSnapshotView``, ``PositionView``, ``ArgumentView``), ConsensusAnalysis
(``ConsensusView``), ClaimValidation (``ClaimVerdictView``) and GovernanceCompliance
(``PositionProvenanceView``). No file here references another bounded context: the application
ports receive these local shapes instead.

``log_position`` and ``snapshot_ref`` are the reproduction anchor (AC 8): regenerating from the same
log position and snapshot must reproduce every section except narrative wording.
"""

from __future__ import annotations

from dataclasses import dataclass

from decision_brief.domain.entities import RejectedProposalRecord
from decision_brief.domain.values import (
    ActorSummary,
    PassageId,
    PositionTimeline,
    RunId,
    TopicOutcome,
)


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """One recorded negotiation step, in log order."""

    round_no: int
    actor: str
    summary: str
    stance: str | None = None


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    """A conflict observed during the run and its holders."""

    topic: str
    summary: str
    holders: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompromiseRecord:
    """A compromise proposal with the positions that carried and opposed it."""

    measure: str
    supporters: tuple[str, ...] = ()
    opponents: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClaimVerdictProjection:
    """A ClaimValidation verdict rendered as statement confidence, never as a fact."""

    claim_id: str
    verdict: str
    passage_ids: tuple[PassageId, ...] = ()


@dataclass(frozen=True, slots=True)
class ConsensusStatement:
    """One agreed statement with its supporters and minorities."""

    topic: str
    statement: str
    supporters: tuple[str, ...] = ()
    minorities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RunProjection:
    """Run history as the brief needs it: sections 1-5 and the disclosure inputs."""

    run_id: RunId
    question: str
    actors: tuple[ActorSummary, ...] = ()
    timelines: tuple[PositionTimeline, ...] = ()
    history: tuple[HistoryEntry, ...] = ()
    conflicts: tuple[ConflictRecord, ...] = ()
    compromises: tuple[CompromiseRecord, ...] = ()
    rejected_proposals: tuple[RejectedProposalRecord, ...] = ()
    blocked_topics: tuple[TopicOutcome, ...] = ()
    claim_verdicts: tuple[ClaimVerdictProjection, ...] = ()
    log_position: int = 0
    snapshot_ref: str = ""


@dataclass(frozen=True, slots=True)
class ConsensusProjection:
    """Derived consensus result as the brief needs it: sections 6-8."""

    run_id: RunId
    statements: tuple[ConsensusStatement, ...] = ()
    majority: tuple[str, ...] = ()
    minority: tuple[str, ...] = ()
    unresolved: tuple[TopicOutcome, ...] = ()
    packages: tuple[str, ...] = ()
    impact: tuple[str, ...] = ()
    log_position: int = 0


@dataclass(frozen=True, slots=True)
class ReproductionInput:
    """Everything regeneration is allowed to read; nothing else may influence the artefact."""

    run: RunProjection
    consensus: ConsensusProjection
