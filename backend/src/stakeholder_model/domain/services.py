"""Domain services of StakeholderModel: materiality policy and attribution rules.

Canonical: .pi/architecture/modules/stakeholder-model.md

CONTRACT FREEZE — strategies and signatures are frozen. The concrete policy and attribution
behaviour is implemented by the selection and weak-attribution issues.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from evidence_corpus.domain.values import SpeakerKind
from stakeholder_model.domain.stakeholder import StakeholderProfile
from stakeholder_model.domain.values import (
    AttributionStrength,
    HistoricalPosition,
    MaterialityScore,
)


@runtime_checkable
class MaterialityScorer(Protocol):
    """Policy that scores how material an institution is for one moderator mandate."""

    def score(self, profile: StakeholderProfile, mandate: str) -> MaterialityScore: ...


class TopicOverlapScorer:
    """Cheap selection policy: overlap between mandate text and interest topics."""

    def score(self, profile: StakeholderProfile, mandate: str) -> MaterialityScore:
        raise NotImplementedError("TopicOverlapScorer.score is implemented by issue #116")


class WeightedInterestScorer:
    """Richer selection policy: weighted overlap using declared interest weights."""

    def score(self, profile: StakeholderProfile, mandate: str) -> MaterialityScore:
        raise NotImplementedError("WeightedInterestScorer.score is implemented by issue #116")


@runtime_checkable
class AttributionRule(Protocol):
    """Decide explicit vs reported vs mention attribution from corpus context."""

    def classify(
        self, speaker_kind: SpeakerKind, *, explicitly_named: bool
    ) -> AttributionStrength: ...


class ExplicitAttribution:
    """The institution is named as the source of the statement."""

    def classify(self, speaker_kind: SpeakerKind, *, explicitly_named: bool) -> AttributionStrength:
        raise NotImplementedError("ExplicitAttribution is implemented by issue #110")


class ReportedAttribution:
    """The statement is reported second-hand by another actor."""

    def classify(self, speaker_kind: SpeakerKind, *, explicitly_named: bool) -> AttributionStrength:
        raise NotImplementedError("ReportedAttribution is implemented by issue #110")


class MentionOnly:
    """The institution appears in passing without stating the position."""

    def classify(self, speaker_kind: SpeakerKind, *, explicitly_named: bool) -> AttributionStrength:
        raise NotImplementedError("MentionOnly is implemented by issue #110")


def select_current_position(
    history: Sequence[HistoricalPosition],
) -> HistoricalPosition | None:
    """Choose the current persona position; weak attribution never overrides explicit (#111)."""
    raise NotImplementedError("select_current_position is implemented by issue #111")
