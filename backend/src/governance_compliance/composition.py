"""Frozen composition factory of GovernanceCompliance (contract freeze, issue #248).

The factory is intentionally not called by ``shared/app.py`` until the runtime-integration
issue. It names every dependency the runtime must provide, including the allowlist source.
"""

from __future__ import annotations

from dataclasses import dataclass

from governance_compliance.application.ports import AllowlistSource
from governance_compliance.application.services import (
    DisclosePositionProvenance,
    EnforceInstitutionOnlyOutput,
    GetPositionProvenance,
    ListAllowlist,
    ListViolations,
    RecordGovernanceViolation,
    ValidateInstitutionalAllowlist,
)
from governance_compliance.application.values import InstitutionalAllowlist
from shared.config import Settings
from shared.db import Database


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
) -> GovernanceComplianceContainer:
    raise NotImplementedError(
        "governance-compliance composition is implemented by the wiring issue"
    )
