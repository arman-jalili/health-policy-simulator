"""Runtime ACLs from NegotiationSession and StakeholderModel (issue #406)."""

from __future__ import annotations

from collections.abc import Sequence

from consensus_analysis.application.ports import MandateThresholdSource
from consensus_analysis.domain.errors import ConsensusAnalysisUnavailable, RunNotClosed
from consensus_analysis.domain.repositories import RunLogPort, StakeholderPowersPort
from consensus_analysis.domain.values import (
    AgendaItem,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    StakeholderId,
    Stance,
    StanceSnapshot,
    TopicRef,
)
from consensus_analysis.infrastructure.acl import StakeholderPowersAcl
from negotiation_session.application.services import GetSimulationRun
from negotiation_session.domain.errors import SimulationRunNotFound
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import RunId as NegotiationRunId
from negotiation_session.infrastructure.upstream import StakeholderProfiles
from stakeholder_model.interfaces.published import StakeholderProfileView


class NegotiationRunLogSource:
    """Read the closed aggregate through its public query service, never its tables."""

    def __init__(self, *, runs: GetSimulationRun) -> None:
        self._runs = runs

    async def _load(self, run_id: RunId) -> SimulationRun:
        try:
            return await self._runs.load(NegotiationRunId(str(run_id)))
        except SimulationRunNotFound as error:
            raise ConsensusAnalysisUnavailable(
                f"no run log exists for {run_id}; derivation cannot invent one"
            ) from error

    async def agenda(self, run_id: RunId) -> Sequence[AgendaItem]:
        run = await self._load(run_id)
        if not run.is_closed:
            raise RunNotClosed(f"run {run_id} is still open")
        topics: list[TopicRef] = []
        topics.extend(TopicRef(topic) for topic in run.conflicts)
        for round_ in run.rounds:
            topics.extend(TopicRef(position.topic) for position in round_.positions.values())
        if not topics:
            topics.append(TopicRef(run.mandate.question))
        return tuple(
            AgendaItem(topic=topic, proposal_class=ProposalClass.OTHER)
            for topic in dict.fromkeys(topics)
        )

    async def stances(self, run_id: RunId) -> Sequence[StanceSnapshot]:
        run = await self._load(run_id)
        if not run.is_closed:
            raise RunNotClosed(f"run {run_id} is still open")
        snapshots: list[StanceSnapshot] = []
        position = 0
        for round_ in run.rounds:
            for item in round_.positions.values():
                if not item.is_open:
                    continue
                position += 1
                snapshots.append(
                    StanceSnapshot(
                        stakeholder=StakeholderId(str(item.stakeholder)),
                        stance=Stance(item.stance.value),
                        topic=TopicRef(item.topic),
                        log_position=LogPosition(position),
                    )
                )
        # No stances is a legitimate domain outcome (everyone abstained), not a missing
        # dependency: the projection records "unresolved" with zero support rather than inventing
        # agreement or reporting an outage.
        return tuple(snapshots)

    async def position_of(
        self, run_id: RunId, stakeholder: StakeholderId, topic: TopicRef
    ) -> LogPosition | None:
        for index, snapshot in enumerate(await self.stances(run_id), start=1):
            if snapshot.stakeholder == stakeholder and snapshot.topic == topic:
                return LogPosition(index)
        return None


class NegotiationMandateThreshold:
    """Read the per-run threshold persisted on the run mandate (no default quorum)."""

    def __init__(self, *, runs: GetSimulationRun) -> None:
        self._runs = runs

    async def threshold(self, run_id: RunId) -> ConsensusThreshold:
        try:
            run = await self._runs.load(NegotiationRunId(str(run_id)))
        except SimulationRunNotFound as error:
            raise ConsensusAnalysisUnavailable(
                f"no mandate exists for {run_id}; a default threshold would be a default quorum"
            ) from error
        return ConsensusThreshold.from_mandate(
            run.mandate.consensus_threshold, label=f"mandate:{run.mandate.id}"
        )


class NegotiationStakeholderPowers:
    """Read veto classes from the same published profile contract the run bound."""

    def __init__(self, *, profiles: StakeholderProfiles) -> None:
        self._profiles = profiles
        self._acl = StakeholderPowersAcl()

    async def veto_classes(
        self, stakeholder_ids: Sequence[StakeholderId]
    ) -> dict[StakeholderId, frozenset[ProposalClass]]:
        wanted = {str(item) for item in stakeholder_ids}
        by_id: dict[str, StakeholderProfileView] = {
            str(profile.stakeholder_id): profile
            for profile in await self._profiles.candidates()
            if str(profile.stakeholder_id) in wanted
        }
        return {
            stakeholder: self._acl.to_veto_classes(by_id[str(stakeholder)])
            for stakeholder in stakeholder_ids
            if str(stakeholder) in by_id
        }


def runtime_run_log(runs: GetSimulationRun) -> RunLogPort:
    return NegotiationRunLogSource(runs=runs)


def runtime_mandate(runs: GetSimulationRun) -> MandateThresholdSource:
    return NegotiationMandateThreshold(runs=runs)


def runtime_powers(profiles: StakeholderProfiles) -> StakeholderPowersPort:
    return NegotiationStakeholderPowers(profiles=profiles)
