"""Use-case results and persistence-facing records (contract freeze, issue #248)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from governance_compliance.application.values import (
    AllowlistEntry,
    GuardDecision,
    GuardRuleId,
    InvocationId,
    PositionId,
    RunId,
    ViolationClass,
    ViolationId,
)


@dataclass(frozen=True, slots=True)
class ViolationRecord:
    """Append-only audit row. ``violation_hash`` is the idempotency key."""

    violation_id: ViolationId
    run_id: RunId
    invocation_id: InvocationId
    violation_class: ViolationClass
    offending_span: str
    rewritten_span: str | None
    rule_id: GuardRuleId
    rule_version: str
    violation_hash: str
    detected_at: datetime


@dataclass(frozen=True, slots=True)
class GuardVerdictResult:
    decision: GuardDecision
    violations: tuple[ViolationRecord, ...]
    rewritten_text: str | None
    rule_version: str


@dataclass(frozen=True, slots=True)
class ProvenanceFacts:
    """Raw facts assembled from NegotiationSession, ClaimValidation and SimulationOrchestration."""

    position_id: PositionId
    evidence_ids: tuple[str, ...]
    argument_ids: tuple[str, ...]
    invocation_id: str | None
    prompt_version: str | None
    model: str | None


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    """Append-only disclosure; one row per position per version."""

    position_id: PositionId
    evidence_ids: tuple[str, ...]
    argument_ids: tuple[str, ...]
    invocation_id: str
    prompt_version: str
    model: str
    disclosed_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class ProvenanceResult:
    record: ProvenanceRecord


@dataclass(frozen=True, slots=True)
class ViolationListResult:
    items: tuple[ViolationRecord, ...]


@dataclass(frozen=True, slots=True)
class AllowlistResult:
    institutions: tuple[AllowlistEntry, ...]
    version: str


@dataclass(frozen=True, slots=True)
class AllowlistValidationResult:
    valid: bool
    institution_count: int
    problems: tuple[str, ...]
