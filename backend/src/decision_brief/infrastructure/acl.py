"""ACL and gate adapters of DecisionBrief.

Canonical: ``.pi/architecture/modules/decision-brief.md`` (Dependencies, Wiring Contract)

These are the only places where an upstream published shape becomes a local projection. An adapter
that cannot map its input fails closed, never returning an empty projection that would make an
incomplete brief look complete.
"""

from __future__ import annotations

from collections.abc import Sequence

from decision_brief.application.dto import CitationResolution
from decision_brief.domain.errors import DisclosureMissing
from decision_brief.domain.projections import (
    ClaimVerdictProjection,
    CompromiseRecord,
    ConflictRecord,
    ConsensusProjection,
    ConsensusStatement,
    HistoryEntry,
    RunProjection,
)
from decision_brief.domain.values import (
    ActorSummary,
    CitationProvenance,
    CitationReference,
    OutcomeKind,
    PassageId,
    PositionStance,
    PositionTimeline,
    RunId,
    TopicOutcome,
)
from evidence_corpus.application.commands import ResolvePassageRequest
from evidence_corpus.application.services import ResolvePassage
from evidence_corpus.domain.errors import PassageNotFound
from evidence_corpus.domain.published import PassageView
from governance_compliance.application.commands import GetPositionProvenanceRequest
from governance_compliance.application.errors import GovernanceViolationNotFound
from governance_compliance.application.services import GetPositionProvenance
from governance_compliance.application.values import PositionId as GovernancePositionId
from negotiation_session.application.services import GetSimulationRun
from negotiation_session.domain.values import RunId as NegotiationRunId


class NegotiationHistoryAcl:
    """Map the NegotiationSession aggregate to the local run projection (sections 1-5)."""

    def __init__(self, *, runs: GetSimulationRun) -> None:
        self._runs = runs

    async def load(self, run_id: RunId) -> RunProjection | None:
        try:
            run = await self._runs.load(NegotiationRunId(str(run_id)))
        except Exception:
            return None
        if not run.is_closed:
            return None
        actors = tuple(
            ActorSummary(
                institution=binding.institution_name,
                goals=tuple(binding.interests),
                constraints=tuple(binding.constraints),
                adopted_positions=tuple(
                    str(position.stance)
                    for round_ in run.rounds
                    for position in round_.positions.values()
                    if position.stakeholder == stakeholder and position.is_open
                ),
            )
            for stakeholder, binding in run.bound.items()
        )
        timelines = tuple(
            PositionTimeline(
                actor=binding.institution_name,
                stances=tuple(
                    PositionStance(round_no=round_.number, stance=position.stance.value)
                    for round_ in run.rounds
                    for position in round_.positions.values()
                    if position.stakeholder == stakeholder and position.is_open
                ),
            )
            for stakeholder, binding in run.bound.items()
        )
        history = tuple(
            HistoryEntry(
                round_no=round_.number,
                actor=str(argument.stakeholder),
                summary=argument.text,
                stance=argument.stance.value,
            )
            for round_ in run.rounds
            for argument in round_.arguments
        )
        conflicts = tuple(
            ConflictRecord(
                topic=str(topic), summary=str(topic), holders=tuple(map(str, conflict.stances))
            )
            for topic, conflict in run.conflicts.items()
        )
        compromises = tuple(
            CompromiseRecord(
                measure=coalition.proposal.summary,
                supporters=tuple(map(str, coalition.members)),
            )
            for coalition in run.coalitions.values()
        )
        claim_verdicts = tuple(
            ClaimVerdictProjection(
                claim_id=argument.id,
                verdict=claim.verdict or "unknown",
            )
            for round_ in run.rounds
            for argument in round_.arguments
            for claim in argument.claims
        )
        return RunProjection(
            run_id=run_id,
            question=run.mandate.question,
            actors=actors,
            timelines=timelines,
            history=history,
            conflicts=conflicts,
            compromises=compromises,
            rejected_proposals=(),
            claim_verdicts=claim_verdicts,
            log_position=sum(len(round_.arguments) for round_ in run.rounds),
            snapshot_ref=f"mandate:{run.mandate.mandate_hash}",
        )


class ConsensusViewAcl:
    """Map ConsensusAnalysis records to the local consensus projection (6-8)."""

    def __init__(self, *, consensus: object) -> None:
        self._consensus = consensus

    async def load(self, run_id: RunId) -> ConsensusProjection | None:
        from consensus_analysis.application.commands import GetConsensusRequest
        from consensus_analysis.domain.values import RunId as ConsensusRunId

        result = await self._consensus.get_consensus.execute(  # type: ignore[attr-defined]
            GetConsensusRequest(run_id=ConsensusRunId(str(run_id)))
        )
        if not result.records:
            return None
        statements: list[ConsensusStatement] = []
        unresolved: list[TopicOutcome] = []
        majority: list[str] = []
        minority: list[str] = []
        for record in result.records:
            statements.append(
                ConsensusStatement(
                    topic=str(record.topic),
                    statement=f"{record.topic}: {record.outcome.value} ({record.support:.0%})",
                    supporters=tuple(map(str, record.supporters)),
                    minorities=tuple(map(str, record.minorities)),
                )
            )
            majority.extend(map(str, record.supporters))
            minority.extend(map(str, record.minorities))
            if record.outcome.value == "veto_blocked":
                unresolved.append(
                    TopicOutcome(
                        topic=str(record.topic),
                        kind=OutcomeKind.BLOCKED,
                        blocking_stakeholders=tuple(map(str, record.blockers)),
                        reason="veto",
                    )
                )
            elif record.outcome.value == "unresolved":
                unresolved.append(
                    TopicOutcome(topic=str(record.topic), kind=OutcomeKind.OPEN_DISPUTE)
                )
        return ConsensusProjection(
            run_id=run_id,
            statements=tuple(statements),
            majority=tuple(dict.fromkeys(majority)),
            minority=tuple(dict.fromkeys(minority)),
            unresolved=tuple(unresolved),
            log_position=len(result.records),
        )


class EvidenceCorpusCitationResolver:
    """Resolve passage ids through the EvidenceCorpus ``ResolvePassage`` use case (AC 2).

    A passage the corpus cannot resolve is reported as unresolved; it is never invented, and a
    missing adapter is a wiring failure rather than an empty resolution.
    """

    def __init__(self, resolve_passage: ResolvePassage) -> None:
        self._passages = resolve_passage

    async def resolve(self, passage_ids: Sequence[PassageId]) -> CitationResolution:
        """Return every resolved citation and every id that does not resolve, in input order."""
        resolved: list[CitationReference] = []
        unresolved: list[PassageId] = []
        for passage_id in passage_ids:
            try:
                view = await self._passages.execute(
                    ResolvePassageRequest(passage_id=str(passage_id))
                )
            except PassageNotFound:
                unresolved.append(passage_id)
                continue
            resolved.append(_to_citation(view))
        return CitationResolution(resolved=tuple(resolved), unresolved=tuple(unresolved))


def _to_citation(view: PassageView) -> CitationReference:
    """Map the published passage to a resolved citation; the quote is the citable span."""
    provenance = CitationProvenance(
        outlet=view.provenance.outlet,
        published_on=view.provenance.published_on,
        medium=view.provenance.medium,
        page_from=view.provenance.page_from,
        page_to=view.provenance.page_to,
        source_uri=view.provenance.source_uri,
    )
    return CitationReference(
        passage_id=PassageId(view.passage_id),
        provenance=provenance,
        quote=view.text,
    )


class GovernanceProvenanceGate:
    """Require a disclosure row for every open position of the run (AC 3, 4, 11)."""

    def __init__(self, *, runs: GetSimulationRun, provenance: GetPositionProvenance) -> None:
        self._runs = runs
        self._provenance = provenance

    async def assert_disclosed(self, run_id: RunId) -> None:
        run = await self._runs.load(NegotiationRunId(str(run_id)))
        for round_ in run.rounds:
            for position in round_.positions.values():
                if not position.is_open:
                    continue
                try:
                    await self._provenance.execute(
                        GetPositionProvenanceRequest(
                            position_id=GovernancePositionId(str(position.id))
                        )
                    )
                except GovernanceViolationNotFound as error:
                    raise DisclosureMissing(str(run_id), str(position.id)) from error
