"""Frozen application services of NegotiationSession (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Service classification, API)

Constructors, service names and ``execute`` signatures are frozen. Bodies raise
``NotImplementedError`` naming the implementing issue; later issues may not rename or remove a
frozen member without a new freeze entry. Business rules stay in the aggregate.
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Mapping, Sequence

from negotiation_session.application.commands import (
    CloseRoundRequest,
    FormCoalitionRequest,
    GetSimulationRunRequest,
    ListConflictTopicsRequest,
    ListRoundLearningRequest,
    ListRoundsRequest,
    OpenSimulationRunRequest,
    RecordAbstentionRequest,
    ReplaySimulationHistoryRequest,
    RevisePositionRequest,
    SelectRelevantStakeholdersRequest,
    SubmitInitialPositionRequest,
    SummariseIntermediateResultRequest,
    TakeNegotiationTurnRequest,
    TrackConflictTopicRequest,
    TranslateQuestionToMandateRequest,
)
from negotiation_session.application.dto import (
    ArgumentResult,
    BoundStakeholderResult,
    CloseRoundResult,
    CoalitionOfferResult,
    CoalitionResult,
    ConflictTopicResult,
    HistoryEventResult,
    IntermediateSummaryResult,
    LearningInsightResult,
    MandateResult,
    OpenSimulationRunResult,
    PositionResult,
    ReplayResult,
    RoundLearningResult,
    RoundSummaryResult,
    SimulationRunResult,
    StakeholderSelectionResult,
    StoppingConditionResult,
)
from negotiation_session.application.mappers import (
    binding_from_profile,
    claim_evidence_from_pack,
    claim_is_admissible,
    guard_rejected,
)
from negotiation_session.application.ports import (
    ClaimVerdictGate,
    Clock,
    EventPublisher,
    EvidencePackReader,
    GovernanceGuard,
    IdFactory,
    InvocationLookup,
    StakeholderDirectory,
    UnitOfWork,
)
from negotiation_session.domain.entities import (
    Coalition,
    ConflictTopic,
    NegotiationMandate,
    NegotiationRound,
    Position,
    RoundLearning,
)
from negotiation_session.domain.errors import (
    ClaimVerdictRejected,
    EvidencePackNotFound,
    GovernanceRejected,
    SimulationRunNotFound,
    StakeholderNotBound,
)
from negotiation_session.domain.events import (
    CoalitionFormed,
    InitialPositionStated,
    LoggedEvent,
    NegotiationPhaseAdvanced,
    PositionRevised,
    RoundOpened,
    SimulationRunClosed,
    SimulationRunOpened,
)
from negotiation_session.domain.repositories import RunEventLog, SimulationRunRepository
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ClaimEvidence,
    CoalitionId,
    ConflictStatus,
    ConsensusLevel,
    EvidencePackId,
    InvocationId,
    MandateId,
    NegotiationPhase,
    PositionId,
    Proposal,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingCondition,
    StoppingConditionName,
    TopicRef,
)
from shared.errors import ValidationFailedError


class TranslateQuestionToMandate:
    """Moderator policy: turn a policy question into a bounded, immutable mandate."""

    def __init__(self, *, clock: Clock, ids: IdFactory) -> None:
        self._clock = clock
        self._ids = ids

    async def execute(self, request: TranslateQuestionToMandateRequest) -> MandateResult:
        return _mandate_result(_build_mandate(request, self._ids))


class SelectRelevantStakeholders:
    """Delegate selection to StakeholderModel and record the rationale."""

    def __init__(self, *, stakeholders: StakeholderDirectory) -> None:
        self._stakeholders = stakeholders

    async def execute(
        self, request: SelectRelevantStakeholdersRequest
    ) -> StakeholderSelectionResult:
        words = {word.lower() for word in request.question.split() if len(word) > 3}
        candidates = await self._stakeholders.candidates()
        ranked: list[tuple[int, str]] = []
        for view in candidates:
            haystack = " ".join(
                [
                    view.identity.name,
                    *(item.topic for item in view.interests),
                    *(item.topic for item in view.constraints),
                    *view.mandate_scope.topics,
                ]
            ).lower()
            score = sum(1 for word in words if word in haystack)
            if score or not words:
                ranked.append((score, view.stakeholder_id))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        selected = tuple(StakeholderId(value) for _, value in ranked[: request.limit])
        return StakeholderSelectionResult(
            stakeholder_ids=selected,
            rationale=f"matched {len(words)} question terms against institutional profiles",
        )


class OpenSimulationRun:
    """Transaction boundary: create the aggregate, bind stakeholders, write the outbox."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        stakeholders: StakeholderDirectory,
        clock: Clock,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._stakeholders = stakeholders
        self._clock = clock
        self._ids = ids
        self._uow = uow

    async def execute(self, request: OpenSimulationRunRequest) -> OpenSimulationRunResult:
        candidate_ids = request.stakeholder_ids or tuple(
            StakeholderId(view.stakeholder_id)
            for view in (await self._stakeholders.candidates())[:12]
        )
        bound: dict[StakeholderId, StakeholderBinding] = {}
        for stakeholder in candidate_ids:
            view = await self._stakeholders.profile(stakeholder)
            if view is None:
                raise StakeholderNotBound(f"stakeholder {stakeholder} is not registered")
            bound[stakeholder] = binding_from_profile(view)
        mandate = _build_mandate(
            TranslateQuestionToMandateRequest(
                question=request.question, round_cap=request.round_cap
            ),
            self._ids,
        )
        run = SimulationRun.open(
            run_id=RunId(self._ids.new_id("run")), mandate=mandate, bound=bound
        )
        async with self._uow.transaction():
            await _persist(run, self._runs, self._event_log, self._events)
        return OpenSimulationRunResult(
            run_id=run.id,
            phase=run.phase,
            mandate=_mandate_result(mandate),
            bound=tuple(_bound_result(binding) for binding in bound.values()),
        )


class SubmitInitialPosition:
    """Load-mutate-save one evidenced starting position."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        evidence: EvidencePackReader,
        guard: GovernanceGuard,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._evidence = evidence
        self._guard = guard
        self._ids = ids
        self._uow = uow

    async def execute(self, request: SubmitInitialPositionRequest) -> PositionResult:
        run = await _require_run(self._runs, request.run_id)
        evidence = await _resolve_evidence(self._evidence, request.evidence_ids)
        await _guard_text(
            self._guard,
            _proposal_text(request.proposal),
            run.id,
            request.stakeholder_id,
        )
        position = run.submit_initial_position(
            request.stakeholder_id,
            request.topic,
            request.stance,
            request.proposal,
            evidence,
        )
        async with self._uow.transaction():
            await _persist(run, self._runs, self._event_log, self._events)
        return _position_result(run.id, position)


class TakeNegotiationTurn:
    """Load-mutate-save one argued turn; claims are gated by verdicts."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        evidence: EvidencePackReader,
        claims: ClaimVerdictGate,
        guard: GovernanceGuard,
        invocations: InvocationLookup,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._evidence = evidence
        self._claims = claims
        self._guard = guard
        self._invocations = invocations
        self._ids = ids
        self._uow = uow

    async def execute(self, request: TakeNegotiationTurnRequest) -> ArgumentResult:
        run = await _require_run(self._runs, request.run_id)
        evidence = await _resolve_evidence(self._evidence, request.evidence_ids)
        for claim in request.claims:
            verdict = await self._claims.verdict_for(claim)
            if not claim_is_admissible(verdict):
                raise ClaimVerdictRejected(
                    f"claim {claim.text!r} was not admitted by its verdict ({verdict.verdict})"
                )
        await _guard_text(
            self._guard,
            request.text,
            run.id,
            request.stakeholder_id,
            request.invocation_id,
        )
        if request.invocation_id is None:
            raise ValidationFailedError("an argument requires its invocation id (ADR-006)")
        await self._invocations.require(run.id, request.invocation_id)
        argument = run.take_turn(
            request.stakeholder_id,
            request.target,
            request.stance,
            request.text,
            request.claims,
            evidence,
            unsupported=request.unsupported,
            invocation_id=request.invocation_id,
        )
        async with self._uow.transaction():
            await _persist(run, self._runs, self._event_log, self._events)
        return _argument_result(run.id, argument)


class RevisePosition:
    """Load-mutate-save a position revision with a causal reason."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        evidence: EvidencePackReader,
        guard: GovernanceGuard,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._evidence = evidence
        self._guard = guard
        self._ids = ids
        self._uow = uow

    async def execute(self, request: RevisePositionRequest) -> PositionResult:
        run = await _require_run(self._runs, request.run_id)
        current = run.position_by_id(request.position_id)
        await _guard_text(
            self._guard,
            request.reason.driver or "position revision",
            run.id,
            current.stakeholder,
        )
        position = run.revise_position(
            current.stakeholder,
            current.topic,
            request.stance,
            request.reason,
        )
        async with self._uow.transaction():
            await _persist(run, self._runs, self._event_log, self._events)
        return _position_result(run.id, position)


class RecordAbstention:
    """Record the absence of a turn so the round-close guard is truthful."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._ids = ids
        self._uow = uow

    async def execute(self, request: RecordAbstentionRequest) -> SimulationRunResult:
        run = await _require_run(self._runs, request.run_id)
        run.record_abstention(request.stakeholder_id, request.topic)
        async with self._uow.transaction():
            await _persist(run, self._runs, self._event_log, self._events)
        return _run_result(run)


class TrackConflictTopic:
    """Formalise a divergence as a tracked conflict with its stance map."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._ids = ids
        self._uow = uow

    async def execute(self, request: TrackConflictTopicRequest) -> ConflictTopicResult:
        run = await _require_run(self._runs, request.run_id)
        conflict = run.track_conflict(request.topic, request.stances)
        async with self._uow.transaction():
            await _persist(run, self._runs, self._event_log, self._events)
        return _conflict_result(run.id, conflict)


class FormCoalition:
    """Orchestrate offers and membership inside the run; no retroactive support."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._ids = ids
        self._uow = uow

    async def execute(self, request: FormCoalitionRequest) -> CoalitionResult:
        run = await _require_run(self._runs, request.run_id)
        coalition = run.form_coalition(
            topic=request.topic,
            member_ids=request.member_ids,
            proposal=request.proposal,
            coalition_id=CoalitionId(self._ids.new_id("coa")),
        )
        async with self._uow.transaction():
            await _persist(run, self._runs, self._event_log, self._events)
        return _coalition_result(run.id, coalition)


class CloseRound:
    """Close the current round with its learning, then evaluate the stopping condition."""

    def __init__(
        self,
        *,
        runs: SimulationRunRepository,
        event_log: RunEventLog,
        events: EventPublisher,
        ids: IdFactory,
        uow: UnitOfWork,
    ) -> None:
        self._runs = runs
        self._event_log = event_log
        self._events = events
        self._ids = ids
        self._uow = uow

    async def execute(self, request: CloseRoundRequest) -> CloseRoundResult:
        run = await _require_run(self._runs, request.run_id)
        run.close_round(request.learning)
        condition = run.evaluate_stopping(_consensus(request.convergence))
        async with self._uow.transaction():
            await _persist(run, self._runs, self._event_log, self._events)
        return CloseRoundResult(
            run_id=run.id,
            round=run.rounds[-1].number,
            learning=_learning_result(run.id, run.rounds[-1].number, request.learning),
            stopping_condition=_stopping_result(condition),
        )


class GetSimulationRun:
    """Read the run's current state without mutating it."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: GetSimulationRunRequest) -> SimulationRunResult:
        return _run_result(await _require_run(self._runs, request.run_id))


class ListRounds:
    """Project round summaries and their learning."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListRoundsRequest) -> Sequence[RoundSummaryResult]:
        run = await _require_run(self._runs, request.run_id)
        rounds = run.rounds[: max(request.limit, 0)]
        return tuple(_round_result(run.id, round_) for round_ in rounds)


class ListConflictTopics:
    """Project tracked conflicts, optionally filtered by status."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListConflictTopicsRequest) -> Sequence[ConflictTopicResult]:
        run = await _require_run(self._runs, request.run_id)
        return tuple(
            _conflict_result(run.id, conflict)
            for conflict in run.conflicts.values()
            if request.status is None or conflict.status is request.status
        )


class ListRoundLearning:
    """Project per-round learning insight sets."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(self, request: ListRoundLearningRequest) -> Sequence[RoundLearningResult]:
        run = await _require_run(self._runs, request.run_id)
        return tuple(
            _learning_result(run.id, round_.number, round_.learning)
            for round_ in run.rounds
            if round_.learning is not None
        )


class SummariseIntermediateResult:
    """Project round state for the moderator; never mutates the run."""

    def __init__(self, *, runs: SimulationRunRepository) -> None:
        self._runs = runs

    async def execute(
        self, request: SummariseIntermediateResultRequest
    ) -> IntermediateSummaryResult:
        run = await _require_run(self._runs, request.run_id)
        current = request.round_number or (run.rounds[-1].number if run.rounds else 0)
        return IntermediateSummaryResult(
            run_id=run.id,
            round=current,
            phase=run.phase,
            consensus="unmeasured",
            open_conflicts=tuple(
                topic
                for topic, conflict in run.conflicts.items()
                if conflict.status is ConflictStatus.OPEN
            ),
            coalition_ids=tuple(run.coalitions),
            argument_count=sum(len(round_.arguments) for round_ in run.rounds),
        )


class ReplaySimulationHistory:
    """Fold the append-only run log to round N and return the reconstructed state (AC 11)."""

    def __init__(self, *, runs: SimulationRunRepository, event_log: RunEventLog) -> None:
        self._runs = runs
        self._event_log = event_log

    async def execute(self, request: ReplaySimulationHistoryRequest) -> ReplayResult:
        run = await self._runs.get(request.run_id)
        if run is None:
            raise SimulationRunNotFound(f"no simulation run {request.run_id}")
        logged = await self._event_log.read(request.run_id, request.until_round)
        return ReplayResult(
            run_id=run.id,
            until_round=request.until_round,
            events=tuple(_history_event(item) for item in logged),
            state=_fold_events(run.id, logged, run.round_cap),
        )


async def _resolve_evidence(
    reader: EvidencePackReader, pack_ids: Sequence[EvidencePackId]
) -> list[ClaimEvidence]:
    references: list[ClaimEvidence] = []
    for pack_id in pack_ids:
        view = await reader.frozen_pack(pack_id)
        if view is None:
            raise EvidencePackNotFound(f"no frozen evidence pack {pack_id}")
        references.extend(claim_evidence_from_pack(view))
    return references


async def _guard_text(
    guard: GovernanceGuard,
    text: str,
    run_id: RunId,
    stakeholder_id: StakeholderId,
    invocation_id: InvocationId | None = None,
) -> None:
    verdict = await guard.enforce(
        text, run_id=run_id, stakeholder_id=stakeholder_id, invocation_id=invocation_id
    )
    if guard_rejected(verdict):
        raise GovernanceRejected(
            "governance guard rejected the text: " + ", ".join(verdict.violations)
        )


def _proposal_text(proposal: Proposal) -> str:
    return " ".join([proposal.summary, *(component.measure for component in proposal.components)])


def _consensus(value: str) -> ConsensusLevel:
    try:
        return ConsensusLevel(value.lower())
    except ValueError:
        return ConsensusLevel.NONE


async def _persist(
    run: SimulationRun,
    runs: SimulationRunRepository,
    event_log: RunEventLog,
    events: EventPublisher,
) -> None:
    drained = run.drain_events()
    await event_log.append(run.id, drained)
    await runs.save(run)
    await events.publish(drained)


def _build_mandate(
    request: TranslateQuestionToMandateRequest, ids: IdFactory
) -> NegotiationMandate:
    conditions = request.stopping_conditions or (
        StoppingConditionName.CONSENSUS,
        StoppingConditionName.ROUND_CAP,
        StoppingConditionName.DEADLOCK,
    )
    return NegotiationMandate(
        id=MandateId(ids.new_id("mnd")),
        question=request.question,
        objective=request.question,
        constraints=request.constraints,
        round_cap=request.round_cap,
        stopping_conditions=conditions,
        profile_version="v1",
        mandate_hash=hashlib.sha256(f"{request.question}|{request.round_cap}".encode()).hexdigest(),
    )


def _bound_result(binding: StakeholderBinding) -> BoundStakeholderResult:
    return BoundStakeholderResult(
        stakeholder_id=binding.stakeholder_id,
        institution_name=binding.institution_name,
        institution_code=binding.institution_code,
        profile_version=binding.profile_version,
        persona_version=binding.persona_version,
    )


def _position_result(run_id: RunId, position: Position) -> PositionResult:
    return PositionResult(
        position_id=position.id,
        run_id=run_id,
        round=position.round_number,
        stakeholder_id=position.stakeholder,
        topic=position.topic,
        stance=position.stance,
        proposal=position.proposal,
        evidence_ids=tuple(item.evidence_id for item in position.evidence),
        supersedes=position.supersedes,
        revision=position.revision,
    )


def _argument_result(run_id: RunId, argument: object) -> ArgumentResult:
    from negotiation_session.domain.entities import Argument

    if not isinstance(argument, Argument):
        raise TypeError("expected an Argument")
    return ArgumentResult(
        argument_id=argument.id,
        run_id=run_id,
        round=argument.round_number,
        stakeholder_id=argument.stakeholder,
        target=argument.target,
        stance=argument.stance,
        evidence_ids=tuple(item.evidence_id for item in argument.evidence),
        unsupported=argument.unsupported,
        invocation_id=argument.invocation_id,
    )


def _coalition_result(run_id: RunId, coalition: Coalition) -> CoalitionResult:
    return CoalitionResult(
        coalition_id=coalition.id,
        run_id=run_id,
        topic=coalition.topic,
        proposal=coalition.proposal,
        members=tuple(coalition.members),
        offers=tuple(
            CoalitionOfferResult(
                offer_id=offer.id,
                invited_id=offer.invited,
                conditions=offer.conditions,
                status=offer.status,
                decline_reason=offer.decline_reason,
            )
            for offer in coalition.offers.values()
        ),
    )


def _stopping_result(condition: StoppingCondition) -> StoppingConditionResult:
    return StoppingConditionResult(
        name=condition.name,
        fired=condition.fired,
        parameters=condition.parameters,
    )


# ── Projection helpers ──────────────────────────────────────────────────────


async def _require_run(runs: SimulationRunRepository, run_id: RunId) -> SimulationRun:
    run = await runs.get(run_id)
    if run is None:
        raise SimulationRunNotFound(f"no simulation run {run_id}")
    return run


def _mandate_result(mandate: NegotiationMandate) -> MandateResult:
    return MandateResult(
        mandate_id=str(mandate.id),
        question=mandate.question,
        objective=mandate.objective,
        constraints=mandate.constraints,
        round_cap=mandate.round_cap,
        stopping_conditions=mandate.stopping_conditions,
        mandate_hash=mandate.mandate_hash,
    )


def _run_result(run: SimulationRun) -> SimulationRunResult:
    return SimulationRunResult(
        run_id=run.id,
        phase=run.phase,
        round=run.rounds[-1].number if run.rounds else 0,
        round_cap=run.round_cap,
        closed=run.is_closed,
        bound_stakeholder_ids=tuple(sorted(run.bound)),
        open_position_ids=tuple(
            sorted(
                position.id
                for round_ in run.rounds
                for position in round_.positions.values()
                if position.is_open
            )
        ),
        coalition_ids=tuple(sorted(run.coalitions)),
    )


def _round_result(run_id: RunId, round_: NegotiationRound) -> RoundSummaryResult:
    return RoundSummaryResult(
        round=round_.number,
        closed=round_.is_closed,
        argument_count=len(round_.arguments),
        abstention_count=len(round_.abstentions),
        learning=(
            _learning_result(run_id, round_.number, round_.learning)
            if round_.learning is not None
            else None
        ),
    )


def _learning_result(
    run_id: RunId, round_number: int, learning: RoundLearning | None
) -> RoundLearningResult:
    if learning is None:
        raise ValueError(f"round {round_number} has no learning record")
    return RoundLearningResult(
        learning_id=learning.id,
        run_id=run_id,
        round=round_number,
        insights=tuple(
            LearningInsightResult(
                insight_type=insight.insight_type.value,
                statement=insight.statement,
                derived_from=insight.derived_from,
                round_number=insight.round_number,
            )
            for insight in learning.insights
        ),
    )


def _conflict_result(run_id: RunId, conflict: ConflictTopic) -> ConflictTopicResult:
    return ConflictTopicResult(
        conflict_id=conflict.id,
        run_id=run_id,
        topic=conflict.topic,
        status=conflict.status,
        stances=dict(conflict.stances),
    )


def _history_event(logged: LoggedEvent) -> HistoryEventResult:
    event = logged.event
    return HistoryEventResult(
        sequence=logged.sequence,
        event_type=getattr(event, "name", type(event).__name__),
        payload=_payload(event),
        occurred_at=logged.occurred_at,
    )


def _payload(event: object) -> Mapping[str, object]:
    return {
        field.name: getattr(event, field.name)
        for field in dataclasses.fields(event)  # type: ignore[arg-type]
    }


def _fold_events(
    run_id: RunId, events: Sequence[LoggedEvent], round_cap: int
) -> SimulationRunResult:
    phase = NegotiationPhase.POSITION_FORMATION
    bound: tuple[StakeholderId, ...] = ()
    current_round = 0
    positions: dict[tuple[StakeholderId, TopicRef], PositionId] = {}
    coalitions: set[CoalitionId] = set()
    closed = False
    for logged in events:
        event = logged.event
        if isinstance(event, SimulationRunOpened):
            bound = event.stakeholder_ids
        elif isinstance(event, RoundOpened):
            current_round = event.round
            phase = event.phase
        elif isinstance(event, (InitialPositionStated, PositionRevised)):
            positions[(event.stakeholder_id, event.topic)] = event.position_id
        elif isinstance(event, CoalitionFormed):
            coalitions.add(event.coalition_id)
        elif isinstance(event, NegotiationPhaseAdvanced):
            phase = event.to_phase
        elif isinstance(event, SimulationRunClosed):
            phase = event.final_phase
            closed = True
    return SimulationRunResult(
        run_id=run_id,
        phase=phase,
        round=current_round,
        round_cap=round_cap,
        closed=closed,
        bound_stakeholder_ids=tuple(sorted(bound)),
        open_position_ids=tuple(sorted(positions.values())),
        coalition_ids=tuple(sorted(coalitions)),
    )


# ── Frozen service classification (ADR-008) ─────────────────────────────────
# Application services load-mutate-save the aggregate or project read models; domain services
# are pure rule evaluation. A name may not move between layers without a new freeze entry.
SERVICE_CLASSIFICATION: Mapping[str, str] = {
    "TranslateQuestionToMandate": "application",
    "SelectRelevantStakeholders": "application",
    "OpenSimulationRun": "application",
    "SubmitInitialPosition": "application",
    "TakeNegotiationTurn": "application",
    "RevisePosition": "application",
    "RecordAbstention": "application",
    "TrackConflictTopic": "application",
    "FormCoalition": "application",
    "CloseRound": "application",
    "GetSimulationRun": "application",
    "ListRounds": "application",
    "ListConflictTopics": "application",
    "ListRoundLearning": "application",
    "SummariseIntermediateResult": "application",
    "ReplaySimulationHistory": "application",
    "EvaluateStoppingCondition": "domain",
    "DetectArgumentContradiction": "domain",
    "TurnOrderPolicy": "domain",
}
