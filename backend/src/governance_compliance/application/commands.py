"""Use-case request DTOs of GovernanceCompliance (contract freeze, issue #248)."""

from __future__ import annotations

from dataclasses import dataclass, field

from governance_compliance.application.values import (
    GuardRuleId,
    InstitutionalAllowlist,
    InvocationId,
    PositionId,
    RunId,
    SpeakerKind,
    ViolationClass,
)


@dataclass(frozen=True, slots=True)
class EnforceInstitutionOnlyOutputRequest:
    """Every argument/position write passes through this request before persistence."""

    text: str
    speaker_kind: SpeakerKind
    invocation_id: InvocationId
    run_id: RunId | None = None
    position_id: PositionId | None = None
    cited_passage_ids: tuple[str, ...] = ()
    reference_figure_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DisclosePositionProvenanceRequest:
    position_id: PositionId
    version: int | None = None
    requested_by: str | None = None


@dataclass(frozen=True, slots=True)
class RecordGovernanceViolationRequest:
    run_id: RunId
    invocation_id: InvocationId
    violation_class: ViolationClass
    offending_span: str
    rewritten_span: str | None
    rule_id: GuardRuleId


@dataclass(frozen=True, slots=True)
class ListViolationsRequest:
    run_id: RunId | None = None
    violation_class: ViolationClass | None = None
    limit: int = field(default=100)


@dataclass(frozen=True, slots=True)
class GetPositionProvenanceRequest:
    position_id: PositionId
    version: int | None = None


@dataclass(frozen=True, slots=True)
class ValidateInstitutionalAllowlistRequest:
    allowlist: InstitutionalAllowlist


@dataclass(frozen=True, slots=True)
class ListAllowlistRequest:
    """The allowlist is bound at boot; this request carries no filters."""
