"""Frozen composition factory of NegotiationSession (contract frozen, issue #282).

The factory is intentionally not called by ``shared/app.py`` until issue #299. It names every
dependency the runtime must provide: the ACLs to EvidenceRetrieval, StakeholderModel,
ClaimValidation, GovernanceCompliance and SimulationOrchestration, plus the progress stream.
"""

from __future__ import annotations

from dataclasses import dataclass

from negotiation_session.application.ports import (
    ClaimVerdictGate,
    EvidencePackReader,
    GovernanceGuard,
    InvocationLookup,
    RunProgressStream,
    StakeholderDirectory,
)
from negotiation_session.application.services import (
    CloseRound,
    FormCoalition,
    GetSimulationRun,
    ListConflictTopics,
    ListRoundLearning,
    ListRounds,
    OpenSimulationRun,
    RecordAbstention,
    ReplaySimulationHistory,
    RevisePosition,
    SelectRelevantStakeholders,
    SubmitInitialPosition,
    SummariseIntermediateResult,
    TakeNegotiationTurn,
    TrackConflictTopic,
    TranslateQuestionToMandate,
)
from shared.config import Settings
from shared.db import Database


@dataclass(frozen=True, slots=True)
class NegotiationSessionContainer:
    translate_question_to_mandate: TranslateQuestionToMandate
    select_relevant_stakeholders: SelectRelevantStakeholders
    open_simulation_run: OpenSimulationRun
    submit_initial_position: SubmitInitialPosition
    take_negotiation_turn: TakeNegotiationTurn
    revise_position: RevisePosition
    record_abstention: RecordAbstention
    track_conflict_topic: TrackConflictTopic
    form_coalition: FormCoalition
    close_round: CloseRound
    get_simulation_run: GetSimulationRun
    list_rounds: ListRounds
    list_conflict_topics: ListConflictTopics
    list_round_learning: ListRoundLearning
    summarise_intermediate_result: SummariseIntermediateResult
    replay_simulation_history: ReplaySimulationHistory
    progress_stream: RunProgressStream


def build_container(
    settings: Settings,
    database: Database,
    *,
    evidence: EvidencePackReader,
    stakeholders: StakeholderDirectory,
    claims: ClaimVerdictGate,
    governance: GovernanceGuard,
    invocations: InvocationLookup,
    progress: RunProgressStream,
) -> NegotiationSessionContainer:
    raise NotImplementedError("negotiation-session composition is implemented by issue #299")
