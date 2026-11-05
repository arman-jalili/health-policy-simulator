"""HTTP container dependency (contract frozen, issue #164)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from claim_validation.application.services import (
    FlagUnsupportedAssertion,
    GetClaim,
    ListContradictions,
    ListReferenceFigures,
    RegisterReferenceFigure,
    ResolveExpertReview,
    VerifyClaim,
)


class ClaimValidationContainer(Protocol):
    verify_claim: VerifyClaim
    flag_unsupported: FlagUnsupportedAssertion
    get_claim: GetClaim
    register_reference_figure: RegisterReferenceFigure
    list_reference_figures: ListReferenceFigures
    list_contradictions: ListContradictions
    resolve_expert_review: ResolveExpertReview


@dataclass(frozen=True, slots=True)
class ContainerView:
    container: ClaimValidationContainer


def get_container(request: Request) -> ClaimValidationContainer:
    container = getattr(request.app.state, "claim_validation", None)
    if container is None:
        raise RuntimeError("claim_validation container is not mounted")
    return container  # type: ignore[no-any-return]
