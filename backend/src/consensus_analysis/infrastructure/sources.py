"""Upstream sources of the derivation inputs (issue #321).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Wiring Contract)

The derivation needs three things from outside this context: the closed run log, the mandate's
threshold and the veto rights per institution. Each is a port; each adapter either serves it or
fails closed with a named reason.

Nothing invents an input. Until NegotiationSession exposes a run-log read model and a mandate
threshold at runtime, ``UnavailableRunLog`` and ``UnavailableMandate`` refuse rather than return an
empty agenda or a default quorum — the two failures that would manufacture agreement.
"""

from __future__ import annotations

from collections.abc import Sequence

from consensus_analysis.application.ports import MandateThresholdSource
from consensus_analysis.domain.errors import ConsensusAnalysisUnavailable
from consensus_analysis.domain.repositories import RunLogPort, StakeholderPowersPort
from consensus_analysis.domain.values import (
    AgendaItem,
    ConsensusThreshold,
    LogPosition,
    ProposalClass,
    RunId,
    StakeholderId,
    StanceSnapshot,
    TopicRef,
)
from consensus_analysis.infrastructure.acl import StakeholderPowersAcl
from stakeholder_model.interfaces.published import StakeholderProfileView

_REASON = (
    "the run-log read model is not exposed by NegotiationSession at runtime yet; "
    "deriving consensus without it would invent stances"
)


class UnavailableRunLog:
    """Fails closed: an empty agenda would silently report 'nothing agreed'."""

    async def agenda(self, run_id: RunId) -> Sequence[AgendaItem]:
        raise ConsensusAnalysisUnavailable(_REASON)

    async def stances(self, run_id: RunId) -> Sequence[StanceSnapshot]:
        raise ConsensusAnalysisUnavailable(_REASON)

    async def position_of(
        self, run_id: RunId, stakeholder: StakeholderId, topic: TopicRef
    ) -> LogPosition | None:
        raise ConsensusAnalysisUnavailable(_REASON)


class UnavailableMandate:
    """Fails closed: a default threshold is a default quorum, which the W8 row forbids."""

    async def threshold(self, run_id: RunId) -> ConsensusThreshold:
        raise ConsensusAnalysisUnavailable(
            "the mandate threshold is not published per run yet; a default threshold "
            "would decide agreement the mandate never granted"
        )


class StakeholderProfilePowers:
    """Reads veto classes from StakeholderModel's published profile contract."""

    def __init__(self, *, profiles: Sequence[StakeholderProfileView]) -> None:
        self._acl = StakeholderPowersAcl()
        self._by_id = {profile.stakeholder_id: profile for profile in profiles}

    async def veto_classes(
        self, stakeholder_ids: Sequence[StakeholderId]
    ) -> dict[StakeholderId, frozenset[ProposalClass]]:
        """Return a map entry per *known* stakeholder; an unknown one holds no veto, unassumed."""
        return {
            stakeholder: self._acl.to_veto_classes(self._by_id[str(stakeholder)])
            for stakeholder in stakeholder_ids
            if str(stakeholder) in self._by_id
        }


class UnavailablePowers:
    """Fails closed: a missing veto map would silently turn a blocked class into consensus."""

    async def veto_classes(
        self, stakeholder_ids: Sequence[StakeholderId]
    ) -> dict[StakeholderId, frozenset[ProposalClass]]:
        raise ConsensusAnalysisUnavailable(
            "veto rights are not published as a bulk read model yet; assuming no veto would "
            "restore consensus for a class an institution can block"
        )


def unavailable_mandate() -> MandateThresholdSource:
    return UnavailableMandate()


def unavailable_run_log() -> RunLogPort:
    return UnavailableRunLog()


def unavailable_powers() -> StakeholderPowersPort:
    return UnavailablePowers()


def powers_from(profiles: Sequence[StakeholderProfileView]) -> StakeholderPowersPort:
    return StakeholderProfilePowers(profiles=profiles)
