"""Composition root of GovernanceCompliance (ADR-001, ADR-009)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from governance_compliance.application.commands import ValidateInstitutionalAllowlistRequest
from governance_compliance.application.dto import ProvenanceFacts
from governance_compliance.application.errors import AllowlistContainsPerson, AllowlistEmpty
from governance_compliance.application.ports import AllowlistSource, FigureVerdictLookup
from governance_compliance.application.repositories import ProvenanceStore, ViolationStore
from governance_compliance.application.rules import (
    ContradictedFigureRule,
    GuardRuleChain,
    InstitutionAliasRule,
    PersonalQuotationRule,
    PersonReferenceRule,
    UnsupportedFactRule,
)
from governance_compliance.application.services import (
    DisclosePositionProvenance,
    EnforceInstitutionOnlyOutput,
    GetPositionProvenance,
    ListAllowlist,
    ListViolations,
    RecordGovernanceViolation,
    ValidateInstitutionalAllowlist,
)
from governance_compliance.application.values import InstitutionalAllowlist, PositionId
from governance_compliance.infrastructure.figures import UnknownFigureVerdicts
from governance_compliance.infrastructure.ner import RegexPersonNameDetector
from governance_compliance.infrastructure.repository.memory import (
    InMemoryProvenanceStore,
    InMemoryViolationStore,
)
from governance_compliance.infrastructure.repository.sqlalchemy import (
    SqlAlchemyProvenanceStore,
    SqlAlchemyViolationStore,
)
from governance_compliance.infrastructure.resolver import AllowlistInstitutionResolver
from shared.clock import SystemClock
from shared.config import Settings
from shared.db import Database
from shared.enums import Persistence
from shared.log_setup import get_logger

logger = get_logger(__name__)


class _NoopUnitOfWork:
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        yield None


@dataclass(frozen=True, slots=True)
class GovernanceComplianceContainer:
    allowlist: InstitutionalAllowlist
    enforce_institution_only_output: EnforceInstitutionOnlyOutput
    disclose_position_provenance: DisclosePositionProvenance
    record_governance_violation: RecordGovernanceViolation
    validate_allowlist: ValidateInstitutionalAllowlist
    list_violations: ListViolations
    get_position_provenance: GetPositionProvenance
    list_allowlist: ListAllowlist


def build_container(
    settings: Settings,
    database: Database | None = None,
    *,
    allowlist_source: AllowlistSource | None = None,
    figure_verdicts: FigureVerdictLookup | None = None,
) -> GovernanceComplianceContainer:
    if allowlist_source is None:
        raise AllowlistEmpty("an allowlist source is required at boot")
    allowlist = allowlist_source.load()
    validation = ValidateInstitutionalAllowlist().execute(
        ValidateInstitutionalAllowlistRequest(allowlist=allowlist)
    )
    if not validation.valid:
        if validation.institution_count == 0:
            raise AllowlistEmpty("institutional allowlist is empty")
        raise AllowlistContainsPerson("; ".join(validation.problems))
    clock = SystemClock()
    uow = _NoopUnitOfWork()
    if settings.persistence is Persistence.POSTGRES:
        if database is None:
            raise ValueError("PERSISTENCE=postgres requires a Database")
        violations: ViolationStore = SqlAlchemyViolationStore(database.session_factory)
        provenance: ProvenanceStore = SqlAlchemyProvenanceStore(database.session_factory)
    else:
        violations = InMemoryViolationStore()
        provenance = InMemoryProvenanceStore()
    chain = GuardRuleChain(
        [
            PersonReferenceRule(RegexPersonNameDetector()),
            PersonalQuotationRule(RegexPersonNameDetector()),
            InstitutionAliasRule(AllowlistInstitutionResolver()),
            UnsupportedFactRule(),
            ContradictedFigureRule(figure_verdicts or UnknownFigureVerdicts()),
        ]
    )
    guard = EnforceInstitutionOnlyOutput(
        rules=chain, allowlist=allowlist, violations=violations, clock=clock, uow=uow
    )
    logger.info(
        "governance_provenance_source_late_bound",
        detail=(
            "the application root binds the NegotiationSession facts source after that "
            "container exists"
        ),
    )
    logger.info(
        "governance_compliance_wired",
        persistence=settings.persistence.value,
        institutions=len(allowlist.institutions),
        rule_version=chain.rule_version,
    )
    return GovernanceComplianceContainer(
        allowlist=allowlist,
        enforce_institution_only_output=guard,
        disclose_position_provenance=DisclosePositionProvenance(
            facts=_NoFacts(), store=provenance, clock=clock, uow=uow
        ),
        record_governance_violation=RecordGovernanceViolation(
            violations=violations, clock=clock, uow=uow
        ),
        validate_allowlist=ValidateInstitutionalAllowlist(),
        list_violations=ListViolations(violations=violations),
        get_position_provenance=GetPositionProvenance(store=provenance),
        list_allowlist=ListAllowlist(allowlist=allowlist),
    )


class _NoFacts:
    async def load(self, position_id: PositionId) -> ProvenanceFacts | None:
        return ProvenanceFacts(
            position_id=position_id,
            evidence_ids=(),
            argument_ids=(),
            invocation_id=None,
            prompt_version=None,
            model=None,
        )
