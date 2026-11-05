"""Application-level audit event; ADR-008 forbids domain events for this context.

The append-only violation row is the source of truth. This event is a transport-friendly
projection for downstream audit consumers, not an aggregate event.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from governance_compliance.application.values import (
    GuardRuleId,
    InvocationId,
    RunId,
    ViolationClass,
    ViolationId,
)


@dataclass(frozen=True, slots=True)
class GovernanceViolationRecorded:
    name: ClassVar[str] = "GovernanceViolationRecorded"
    violation_id: ViolationId
    run_id: RunId
    invocation_id: InvocationId
    violation_class: ViolationClass
    rule_id: GuardRuleId
    detected_at: datetime


GovernanceEvent = GovernanceViolationRecorded
