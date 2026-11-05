"""Frozen application services of GovernanceCompliance (contract freeze, issue #248).

Canonical: .pi/architecture/modules/governance-compliance.md

Constructors, names and ``execute`` signatures are frozen. Bodies raise ``NotImplementedError``
naming the implementing component; later issues may not rename or remove a frozen member.
"""

from __future__ import annotations

from governance_compliance.application.commands import (
    DisclosePositionProvenanceRequest,
    EnforceInstitutionOnlyOutputRequest,
    GetPositionProvenanceRequest,
    ListAllowlistRequest,
    ListViolationsRequest,
    RecordGovernanceViolationRequest,
    ValidateInstitutionalAllowlistRequest,
)
from governance_compliance.application.dto import (
    AllowlistResult,
    AllowlistValidationResult,
    GuardVerdictResult,
    ProvenanceResult,
    ViolationListResult,
    ViolationRecord,
)
from governance_compliance.application.ports import (
    Clock,
    ProvenanceFactsSource,
    UnitOfWork,
)
from governance_compliance.application.repositories import ProvenanceStore, ViolationStore
from governance_compliance.application.rules import GuardRuleChain
from governance_compliance.application.values import InstitutionalAllowlist


class EnforceInstitutionOnlyOutput:
    """Blocking pre-persistence guard over the deterministic rule chain (FR-025)."""

    def __init__(
        self,
        *,
        rules: GuardRuleChain,
        allowlist: InstitutionalAllowlist,
        violations: ViolationStore,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._rules = rules
        self._allowlist = allowlist
        self._violations = violations
        self._clock = clock
        self._uow = uow

    async def execute(self, request: EnforceInstitutionOnlyOutputRequest) -> GuardVerdictResult:
        raise NotImplementedError("EnforceInstitutionOnlyOutput is implemented by GC-001..GC-005")


class DisclosePositionProvenance:
    """Assemble and persist the derivation record for one position (FR-026)."""

    def __init__(
        self,
        *,
        facts: ProvenanceFactsSource,
        store: ProvenanceStore,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._facts = facts
        self._store = store
        self._clock = clock
        self._uow = uow

    async def execute(self, request: DisclosePositionProvenanceRequest) -> ProvenanceResult:
        raise NotImplementedError(
            "DisclosePositionProvenance is implemented by the provenance issue"
        )


class RecordGovernanceViolation:
    """Persist exactly one violation row per deterministic hash; retries are idempotent."""

    def __init__(self, *, violations: ViolationStore, clock: Clock, uow: UnitOfWork) -> None:
        self._violations = violations
        self._clock = clock
        self._uow = uow

    async def execute(self, request: RecordGovernanceViolationRequest) -> ViolationRecord:
        raise NotImplementedError(
            "RecordGovernanceViolation is implemented by the persistence issue"
        )


class ValidateInstitutionalAllowlist:
    """Boot/operator check: non-empty, institution-only, no natural person."""

    def __init__(self) -> None:
        pass

    def execute(self, request: ValidateInstitutionalAllowlistRequest) -> AllowlistValidationResult:
        raise NotImplementedError(
            "ValidateInstitutionalAllowlist is implemented by the allowlist issue"
        )


class ListViolations:
    def __init__(self, *, violations: ViolationStore) -> None:
        self._violations = violations

    async def execute(self, request: ListViolationsRequest) -> ViolationListResult:
        raise NotImplementedError("ListViolations is implemented by the read-model issue")


class GetPositionProvenance:
    def __init__(self, *, store: ProvenanceStore) -> None:
        self._store = store

    async def execute(self, request: GetPositionProvenanceRequest) -> ProvenanceResult:
        raise NotImplementedError("GetPositionProvenance is implemented by the read-model issue")


class ListAllowlist:
    def __init__(self, *, allowlist: InstitutionalAllowlist) -> None:
        self._allowlist = allowlist

    async def execute(self, request: ListAllowlistRequest) -> AllowlistResult:
        raise NotImplementedError("ListAllowlist is implemented by the read-model issue")
