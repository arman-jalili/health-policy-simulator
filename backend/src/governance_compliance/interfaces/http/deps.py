"""HTTP container dependency (contract frozen, issue #248)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from governance_compliance.application.errors import GuardUnavailable
from governance_compliance.application.services import (
    DisclosePositionProvenance,
    EnforceInstitutionOnlyOutput,
    GetPositionProvenance,
    ListAllowlist,
    ListViolations,
    RecordGovernanceViolation,
    ValidateInstitutionalAllowlist,
)


class GovernanceContainer(Protocol):
    enforce_institution_only_output: EnforceInstitutionOnlyOutput
    disclose_position_provenance: DisclosePositionProvenance
    record_governance_violation: RecordGovernanceViolation
    validate_allowlist: ValidateInstitutionalAllowlist
    list_violations: ListViolations
    get_position_provenance: GetPositionProvenance
    list_allowlist: ListAllowlist


@dataclass(frozen=True, slots=True)
class ContainerView:
    container: GovernanceContainer


def get_container(request: Request) -> GovernanceContainer:
    container = getattr(request.app.state, "governance_compliance", None)
    if container is None:
        raise GuardUnavailable("governance_compliance container is not mounted")
    return container  # type: ignore[no-any-return]
