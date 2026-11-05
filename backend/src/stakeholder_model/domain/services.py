"""Domain services of StakeholderModel: materiality policy and attribution rules.

Canonical: .pi/architecture/modules/stakeholder-model.md

CONTRACT FREEZE — strategies and signatures are frozen. The concrete policy and attribution
behaviour is implemented by the selection and weak-attribution issues.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from evidence_corpus.domain.values import SpeakerKind
from stakeholder_model.domain.stakeholder import StakeholderProfile
from stakeholder_model.domain.values import (
    AttributionStrength,
    HistoricalPosition,
    MaterialityScore,
)

_TERM_PATTERN = re.compile(r"[a-z0-9äöüß]+")
_GERMAN_STOPWORDS = frozenset(
    {"der", "die", "das", "den", "dem", "des", "und", "oder", "auf", "für", "mit", "von", "zu"}
)
_TOPIC_ALIASES: dict[str, frozenset[str]] = {
    "waiting_times": frozenset(
        {
            "waiting_times",
            "waiting",
            "wait",
            "wartezeit",
            "wartezeiten",
            "kassenstelle",
            "kassenstellen",
        }
    ),
    "benefits": frozenset(
        {"benefits", "benefit", "leistung", "leistungen", "statutory_benefit_change"}
    ),
    "premiums": frozenset({"premiums", "premium", "beitrag", "beiträge", "beitraege"}),
    "fee_schedule": frozenset({"fee_schedule", "honorar", "honorare", "tarif", "tarife"}),
    "hospital_plan": frozenset({"hospital_plan", "spital", "spitaeler", "spitäler", "krankenhaus"}),
    "service_catalogue": frozenset({"service_catalogue", "leistungskatalog", "service"}),
    "public_health": frozenset(
        {"public_health", "öffentliche_gesundheit", "praevention", "prävention"}
    ),
    "patient_rights": frozenset({"patient_rights", "patientenrechte", "patient"}),
    "workforce": frozenset({"workforce", "personal", "ärzte", "aerzte", "pflege"}),
    "budget_frame": frozenset({"budget_frame", "budget", "finanzrahmen"}),
}


def _terms(text: str) -> set[str]:
    return {
        term for term in _TERM_PATTERN.findall(text.casefold()) if term not in _GERMAN_STOPWORDS
    }


def _topic_matches(topic: str, goal: str, mandate_terms: set[str]) -> bool:
    aliases = _TOPIC_ALIASES.get(topic, frozenset({topic}))
    if mandate_terms & aliases:
        return True
    return bool(_terms(f"{topic} {goal}") & mandate_terms)


@runtime_checkable
class MaterialityScorer(Protocol):
    """Policy that scores how material an institution is for one moderator mandate."""

    def score(self, profile: StakeholderProfile, mandate: str) -> MaterialityScore: ...


class TopicOverlapScorer:
    """Cheap selection policy: fraction of declared interests the mandate touches."""

    def score(self, profile: StakeholderProfile, mandate: str) -> MaterialityScore:
        if not profile.interests:
            return MaterialityScore(0.0)
        terms = _terms(mandate)
        matched = sum(
            1
            for interest in profile.interests
            if _topic_matches(interest.topic, interest.goal, terms)
        )
        return MaterialityScore(matched / len(profile.interests))


class WeightedInterestScorer:
    """Richer selection policy: weighted overlap using declared interest weights."""

    def score(self, profile: StakeholderProfile, mandate: str) -> MaterialityScore:
        total = sum(interest.weight for interest in profile.interests)
        if total <= 0.0:
            return MaterialityScore(0.0)
        terms = _terms(mandate)
        matched = sum(
            interest.weight
            for interest in profile.interests
            if _topic_matches(interest.topic, interest.goal, terms)
        )
        return MaterialityScore(matched / total)


@runtime_checkable
class AttributionRule(Protocol):
    """Decide explicit vs reported vs mention attribution from corpus context."""

    def classify(
        self, speaker_kind: SpeakerKind, *, explicitly_named: bool
    ) -> AttributionStrength: ...


class ExplicitAttribution:
    """The institution itself is named as the source of the statement."""

    def classify(self, speaker_kind: SpeakerKind, *, explicitly_named: bool) -> AttributionStrength:
        """Return explicit only for a named institutional statement; otherwise mention."""
        if speaker_kind is SpeakerKind.INSTITUTION and explicitly_named:
            return AttributionStrength.EXPLICIT
        return AttributionStrength.MENTION


class ReportedAttribution:
    """The statement is reported second-hand by another actor."""

    def classify(self, speaker_kind: SpeakerKind, *, explicitly_named: bool) -> AttributionStrength:
        """Reported speech is second-hand; anonymous talk remains a mere mention."""
        if speaker_kind is SpeakerKind.PERSON:
            return AttributionStrength.REPORTED
        return AttributionStrength.MENTION


class MentionOnly:
    """The institution appears in passing without stating the position."""

    def classify(self, speaker_kind: SpeakerKind, *, explicitly_named: bool) -> AttributionStrength:
        """A passing reference never establishes a position."""
        return AttributionStrength.MENTION


class CorpusAttributionRule:
    """Compose the three strategies from corpus speaker context."""

    def classify(self, speaker_kind: SpeakerKind, *, explicitly_named: bool) -> AttributionStrength:
        """Explicit institutional speech wins; otherwise reported/person or mention."""
        if speaker_kind is SpeakerKind.INSTITUTION and explicitly_named:
            return AttributionStrength.EXPLICIT
        if speaker_kind is SpeakerKind.PERSON:
            return AttributionStrength.REPORTED
        return AttributionStrength.MENTION


def select_current_position(
    history: Sequence[HistoricalPosition],
) -> HistoricalPosition | None:
    """Choose the current persona position.

    Only usable (explicit) positions can establish the current stance. A weak mention never
    overrides an explicit statement, even when it is more recent; if no explicit position exists,
    the result is ``None`` rather than a fabricated stance.
    """
    usable = [position for position in history if position.usable]
    if not usable:
        return None
    return max(usable, key=lambda position: (position.stated_on, position.id))
