"""Views published to NegotiationSession and DecisionBrief (contract freeze, issue #248)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from governance_compliance.application.dto import GuardVerdictResult, ProvenanceRecord


@dataclass(frozen=True, slots=True)
class GuardVerdictView:
    """The only guard shape NegotiationSession may consume before persistence."""

    decision: str
    violations: tuple[str, ...]
    rewritten_text: str | None
    rule_version: str


@dataclass(frozen=True, slots=True)
class PositionProvenanceView:
    """Complete derivation record required before a brief is published."""

    position_id: str
    evidence_ids: tuple[str, ...]
    argument_ids: tuple[str, ...]
    invocation_id: str
    prompt_version: str
    model: str
    disclosed_at: datetime


def to_guard_verdict_view(result: GuardVerdictResult) -> GuardVerdictView:
    return GuardVerdictView(
        decision=result.decision.value,
        violations=tuple(item.violation_class.value for item in result.violations),
        rewritten_text=result.rewritten_text,
        rule_version=result.rule_version,
    )


def to_position_provenance_view(record: ProvenanceRecord) -> PositionProvenanceView:
    return PositionProvenanceView(
        position_id=str(record.position_id),
        evidence_ids=record.evidence_ids,
        argument_ids=record.argument_ids,
        invocation_id=record.invocation_id,
        prompt_version=record.prompt_version,
        model=record.model,
        disclosed_at=record.disclosed_at,
    )
