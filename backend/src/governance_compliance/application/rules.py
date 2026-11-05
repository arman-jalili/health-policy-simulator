"""Deterministic guard rules as application collaborators (contract freeze, issue #248).

ADR-008 service depth: these are stateless policy objects, not aggregates. No LLM decides
compliance. Bodies are TODO until the component issues land; signatures are frozen now.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from governance_compliance.application.ports import (
    FigureVerdictLookup,
    InstitutionResolver,
    PersonNameDetector,
)
from governance_compliance.application.values import (
    GuardDecision,
    GuardRuleId,
    InstitutionalAllowlist,
    SpeakerKind,
    ViolationClass,
)


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
    """Everything a deterministic rule may read. There is no LLM client in this context."""

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
    """GC-001: an agent output may not name a natural person."""

    rule_id = GuardRuleId.GC_001

    def __init__(self, detector: PersonNameDetector) -> None:
        self._detector = detector

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        raise NotImplementedError("GC-001 is implemented in the governance-compliance epic")


class PersonalQuotationRule:
    """GC-002: a direct quotation attributed to a person is rejected."""

    rule_id = GuardRuleId.GC_002

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        raise NotImplementedError("GC-002 is implemented in the governance-compliance epic")


class InstitutionAliasRule:
    """GC-003: a person-owned ministry reference is rewritten or rejected."""

    rule_id = GuardRuleId.GC_003

    def __init__(self, resolver: InstitutionResolver) -> None:
        self._resolver = resolver

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        raise NotImplementedError("GC-003 is implemented in the governance-compliance epic")


class UnsupportedFactRule:
    """GC-004: an uncited factual claim becomes ``unsupported``, never accept."""

    rule_id = GuardRuleId.GC_004

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        raise NotImplementedError("GC-004 is implemented in the governance-compliance epic")


class ContradictedFigureRule:
    """GC-005: a figure contradicted by ClaimValidation is rejected."""

    rule_id = GuardRuleId.GC_005

    def __init__(self, verdicts: FigureVerdictLookup) -> None:
        self._verdicts = verdicts

    async def evaluate(self, context: GuardRuleContext) -> RuleResult:
        raise NotImplementedError("GC-005 is implemented in the governance-compliance epic")


class GuardRuleChain:
    """Fixed-order chain of responsibility. First non-accept rule wins."""

    def __init__(self, rules: Sequence[GuardRule]) -> None:
        self._rules = tuple(rules)

    @property
    def rule_version(self) -> str:
        return "+".join(rule.rule_id.value for rule in self._rules)

    async def evaluate(self, context: GuardRuleContext) -> Sequence[RuleResult]:
        raise NotImplementedError("GuardRuleChain is implemented in the governance-compliance epic")
