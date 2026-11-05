"""Deterministic guard rules as application collaborators (implemented epic)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, cast, runtime_checkable

from governance_compliance.application.ports import (
    FigureVerdictLookup,
    InstitutionResolver,
    PersonNameDetector,
)
from governance_compliance.application.values import (
    FigureVerdict,
    GuardDecision,
    GuardRuleId,
    InstitutionalAllowlist,
    SpeakerKind,
    ViolationClass,
)

_QUOTE = re.compile(r'["„“”\']([^"„“”\']{2,})["„“”\']')
_MINISTER = re.compile(
    r"\b(?:the\s+)?(?:minister(?:'s)?\s+ministry|ministerium\s+des\s+ministers)\b",
    re.IGNORECASE,
)
_FACT = re.compile(
    r"\b(?:ist|sind|beträgt|steigt|sinkt|kostet|erhöht|senkt|prognose|prognostiziert)\b",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"\b\d[\d.,]*\b")


def _remove_spans(text: str, spans: Sequence[tuple[int, int]]) -> str:
    for start, end in sorted(spans, reverse=True):
        text = f"{text[:start]}[person]{text[end:]}"
    return text


@dataclass(frozen=True, slots=True)
class RuleResult:
    rule_id: GuardRuleId
    decision: GuardDecision
    violation_class: ViolationClass | None = None
    offending_span: str | None = None
    rewritten_span: str | None = None
    rewritten_text: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class GuardRuleContext:
    text: str
    speaker_kind: SpeakerKind
    allowlist: InstitutionalAllowlist
    cited_passage_ids: tuple[str, ...]
    reference_figure_ids: tuple[str, ...]
    person_detector: PersonNameDetector
    institution_resolver: InstitutionResolver
    figure_verdicts: FigureVerdictLookup


@runtime_checkable
class GuardRule(Protocol):
    rule_id: GuardRuleId

    async def evaluate(self, context: GuardRuleContext) -> RuleResult: ...


class PersonReferenceRule:
    rule_id = GuardRuleId.GC_001

    def __init__(self, detector: PersonNameDetector) -> None:
        self._detector = detector

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        references = tuple(self._detector.detect(context.text))
        if not references:
            return RuleResult(self.rule_id, GuardDecision.ACCEPT)
        spans = [(item.span.start, item.span.end) for item in references]
        first = references[0]
        return RuleResult(
            self.rule_id,
            GuardDecision.REWRITE,
            ViolationClass.PERSON_NAMED,
            offending_span=first.text,
            rewritten_span="[person]",
            rewritten_text=_remove_spans(context.text, spans),
            reason="natural person named in agent output",
        )


class PersonalQuotationRule:
    rule_id = GuardRuleId.GC_002

    def __init__(self, detector: PersonNameDetector) -> None:
        self._detector = detector

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        match = _QUOTE.search(context.text)
        if match is None:
            return RuleResult(self.rule_id, GuardDecision.ACCEPT)
        person_attributed = bool(self._detector.detect(context.text))
        if context.speaker_kind is not SpeakerKind.PERSON and not person_attributed:
            return RuleResult(self.rule_id, GuardDecision.ACCEPT)
        return RuleResult(
            self.rule_id,
            GuardDecision.REJECT,
            ViolationClass.PERSONAL_QUOTATION,
            offending_span=match.group(0),
            reason="direct quotation attributed to a natural person",
        )


class InstitutionAliasRule:
    rule_id = GuardRuleId.GC_003

    def __init__(self, resolver: InstitutionResolver) -> None:
        self._resolver = resolver

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        match = _MINISTER.search(context.text)
        if match is None:
            return RuleResult(self.rule_id, GuardDecision.ACCEPT)
        resolved = self._resolver.resolve(match.group(0), context.allowlist)
        if resolved is None:
            return RuleResult(
                self.rule_id,
                GuardDecision.REJECT,
                ViolationClass.INSTITUTION_AMBIGUOUS,
                offending_span=match.group(0),
                reason="person-owned institution has no canonical allowlist name",
            )
        return RuleResult(
            self.rule_id,
            GuardDecision.REWRITE,
            ViolationClass.INSTITUTION_AMBIGUOUS,
            offending_span=match.group(0),
            rewritten_span=resolved,
            rewritten_text=context.text.replace(match.group(0), resolved),
            reason="institution alias resolved to canonical name",
        )


class UnsupportedFactRule:
    rule_id = GuardRuleId.GC_004

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        if context.cited_passage_ids or context.reference_figure_ids:
            return RuleResult(self.rule_id, GuardDecision.ACCEPT)
        if not (_FACT.search(context.text) or _NUMBER.search(context.text)):
            return RuleResult(self.rule_id, GuardDecision.ACCEPT)
        return RuleResult(
            self.rule_id,
            GuardDecision.REWRITE,
            ViolationClass.UNSUPPORTED_FACT,
            offending_span=context.text,
            rewritten_span="unsupported",
            rewritten_text=f"unsupported: {context.text}",
            reason="uncited claim presented as fact",
        )


class ContradictedFigureRule:
    rule_id = GuardRuleId.GC_005

    def __init__(self, verdicts: FigureVerdictLookup) -> None:
        self._verdicts = verdicts

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        for figure_id in context.reference_figure_ids:
            verdict = await self._verdicts.verdict_for(figure_id)
            if verdict is FigureVerdict.CONTRADICTED:
                return RuleResult(
                    self.rule_id,
                    GuardDecision.REJECT,
                    ViolationClass.CONTRADICTED_FIGURE,
                    offending_span=figure_id,
                    reason="figure contradicted by the reference figure",
                )
        return RuleResult(self.rule_id, GuardDecision.ACCEPT)


class GuardRuleChain:
    def __init__(self, rules: Sequence[GuardRule]) -> None:
        self._rules = tuple(rules)

    @property
    def rule_version(self) -> str:
        return "+".join(rule.rule_id.value for rule in self._rules)

    async def evaluate(self, context: GuardRuleContext) -> Sequence[RuleResult]:
        """Evaluate every rule; callers aggregate by severity (REJECT > REWRITE > ACCEPT)."""
        return tuple([await rule.evaluate(context) for rule in self._rules])


def context_for(
    *,
    text: str,
    speaker_kind: SpeakerKind,
    allowlist: InstitutionalAllowlist,
    cited_passage_ids: tuple[str, ...],
    reference_figure_ids: tuple[str, ...],
) -> GuardRuleContext:
    """Rules carry their own adapters; context ports are structural placeholders."""
    return GuardRuleContext(
        text=text,
        speaker_kind=speaker_kind,
        allowlist=allowlist,
        cited_passage_ids=cited_passage_ids,
        reference_figure_ids=reference_figure_ids,
        person_detector=cast(PersonNameDetector, None),
        institution_resolver=cast(InstitutionResolver, None),
        figure_verdicts=cast(FigureVerdictLookup, None),
    )
