"""Application services of GovernanceCompliance (implemented governance epic)."""

from __future__ import annotations

import hashlib
import re

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
    ProvenanceRecord,
    ProvenanceResult,
    ViolationListResult,
    ViolationRecord,
)
from governance_compliance.application.errors import (
    GovernanceViolationNotFound,
    ProvenanceIncomplete,
)
from governance_compliance.application.ports import (
    Clock,
    ProvenanceFactsSource,
    UnitOfWork,
)
from governance_compliance.application.repositories import ProvenanceStore, ViolationStore
from governance_compliance.application.rules import GuardRuleChain, context_for
from governance_compliance.application.values import (
    GuardDecision,
    GuardRuleId,
    InstitutionalAllowlist,
    InvocationId,
    RunId,
    ViolationClass,
    ViolationId,
)
from shared.metrics import METRICS

_PERSON_TITLE = re.compile(r"\b(?:Dr\.|Mag\.|Prof\.|Obmann|Obfrau|Präsident(?:in)?)\s+\S+")


def _violation_hash(
    *,
    run_id: RunId,
    invocation_id: InvocationId,
    violation_class: ViolationClass,
    offending_span: str,
    rule_id: GuardRuleId,
    text: str,
) -> str:
    material = (
        f"{run_id}|{invocation_id}|{violation_class.value}|{offending_span}|{rule_id.value}|{text}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


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
        context = context_for(
            text=request.text,
            speaker_kind=request.speaker_kind,
            allowlist=self._allowlist,
            cited_passage_ids=request.cited_passage_ids,
            reference_figure_ids=request.reference_figure_ids,
        )
        results = await self._rules.evaluate(context)
        violations = tuple(
            result for result in results if result.decision is not GuardDecision.ACCEPT
        )
        if not violations:
            METRICS.increment("governance_guard_checks_total", labels={"decision": "accept"})
            return GuardVerdictResult(
                decision=GuardDecision.ACCEPT,
                violations=(),
                rewritten_text=None,
                rule_version=self._rules.rule_version,
            )
        decision = (
            GuardDecision.REJECT
            if any(result.decision is GuardDecision.REJECT for result in violations)
            else GuardDecision.REWRITE
        )
        run_id = request.run_id or RunId("")
        records: list[ViolationRecord] = []
        for result in violations:
            violation_class = result.violation_class or ViolationClass.PERSON_NAMED
            offending = result.offending_span or request.text
            digest = _violation_hash(
                run_id=run_id,
                invocation_id=request.invocation_id,
                violation_class=violation_class,
                offending_span=offending,
                rule_id=result.rule_id,
                text=request.text,
            )
            records.append(
                ViolationRecord(
                    violation_id=ViolationId("vio_" + digest[:26]),
                    run_id=run_id,
                    invocation_id=request.invocation_id,
                    violation_class=violation_class,
                    offending_span=offending,
                    rewritten_span=result.rewritten_span,
                    rule_id=result.rule_id,
                    rule_version=self._rules.rule_version,
                    violation_hash=digest,
                    detected_at=self._clock.now(),
                )
            )
        async with self._uow.transaction():
            for record in records:
                await self._violations.add(record)
        METRICS.increment("governance_guard_checks_total", labels={"decision": decision.value})
        for record in records:
            METRICS.increment(
                "governance_violations_total", labels={"class": record.violation_class.value}
            )
        rewritten = next(
            (
                result.rewritten_text
                for result in violations
                if result.decision is GuardDecision.REWRITE
            ),
            None,
        )
        return GuardVerdictResult(
            decision=decision,
            violations=tuple(records),
            rewritten_text=rewritten,
            rule_version=self._rules.rule_version,
        )


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
        facts = await self._facts.load(request.position_id)
        if facts is None:
            raise ProvenanceIncomplete("position facts are missing")
        missing = [
            name
            for name, value in (
                ("evidence", facts.evidence_ids),
                ("arguments", facts.argument_ids),
                ("invocation", facts.invocation_id),
                ("prompt_version", facts.prompt_version),
                ("model", facts.model),
            )
            if not value
        ]
        if missing:
            raise ProvenanceIncomplete("provenance is incomplete: " + ", ".join(missing))
        existing = await self._store.list_for_position(request.position_id)
        version = request.version or (max((row.version for row in existing), default=0) + 1)
        record = ProvenanceRecord(
            position_id=request.position_id,
            evidence_ids=facts.evidence_ids,
            argument_ids=facts.argument_ids,
            invocation_id=facts.invocation_id or "",
            prompt_version=facts.prompt_version or "",
            model=facts.model or "",
            disclosed_at=self._clock.now(),
            version=version,
        )
        async with self._uow.transaction():
            await self._store.save(record)
        METRICS.increment("governance_provenance_disclosures_total")
        return ProvenanceResult(record)


class RecordGovernanceViolation:
    """Persist exactly one violation row per deterministic hash; retries are idempotent."""

    def __init__(self, *, violations: ViolationStore, clock: Clock, uow: UnitOfWork) -> None:
        self._violations = violations
        self._clock = clock
        self._uow = uow

    async def execute(self, request: RecordGovernanceViolationRequest) -> ViolationRecord:
        digest = _violation_hash(
            run_id=request.run_id,
            invocation_id=request.invocation_id,
            violation_class=request.violation_class,
            offending_span=request.offending_span,
            rule_id=request.rule_id,
            text=request.offending_span,
        )
        record = ViolationRecord(
            violation_id=ViolationId("vio_" + digest[:26]),
            run_id=request.run_id,
            invocation_id=request.invocation_id,
            violation_class=request.violation_class,
            offending_span=request.offending_span,
            rewritten_span=request.rewritten_span,
            rule_id=request.rule_id,
            rule_version=request.rule_id.value,
            violation_hash=digest,
            detected_at=self._clock.now(),
        )
        async with self._uow.transaction():
            return await self._violations.add(record)


class ValidateInstitutionalAllowlist:
    """Boot/operator check: non-empty, institution-only, no natural person."""

    def __init__(self) -> None:
        pass

    def execute(self, request: ValidateInstitutionalAllowlistRequest) -> AllowlistValidationResult:
        problems: list[str] = []
        if request.allowlist.is_empty:
            problems.append("allowlist is empty")
        for entry in request.allowlist.institutions:
            if _PERSON_TITLE.search(entry.canonical_name) or _PERSON_TITLE.search(entry.short_name):
                problems.append(f"{entry.code} looks like a natural person")
        return AllowlistValidationResult(
            valid=not problems,
            institution_count=len(request.allowlist.institutions),
            problems=tuple(problems),
        )


class ListViolations:
    def __init__(self, *, violations: ViolationStore) -> None:
        self._violations = violations

    async def execute(self, request: ListViolationsRequest) -> ViolationListResult:
        rows = await self._violations.list(
            run_id=request.run_id,
            violation_class=request.violation_class,
            limit=request.limit,
        )
        return ViolationListResult(tuple(rows))


class GetPositionProvenance:
    def __init__(self, *, store: ProvenanceStore) -> None:
        self._store = store

    async def execute(self, request: GetPositionProvenanceRequest) -> ProvenanceResult:
        record = await self._store.get(request.position_id, request.version)
        if record is None:
            raise GovernanceViolationNotFound(f"no provenance for position {request.position_id}")
        return ProvenanceResult(record)


class ListAllowlist:
    def __init__(self, *, allowlist: InstitutionalAllowlist) -> None:
        self._allowlist = allowlist

    async def execute(self, request: ListAllowlistRequest) -> AllowlistResult:
        return AllowlistResult(
            institutions=self._allowlist.institutions,
            version=self._allowlist.version,
        )
