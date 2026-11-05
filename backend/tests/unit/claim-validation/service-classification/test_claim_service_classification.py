"""Contract freeze: services live in the correct layer (issue #164)."""

from __future__ import annotations

from tests.unit.claim_validation_contract_helpers import method_names

from claim_validation.application.services import (
    FlagUnsupportedAssertion,
    GetClaim,
    ListContradictions,
    ListReferenceFigures,
    RegisterReferenceFigure,
    ResolveExpertReview,
    VerifyClaim,
)
from claim_validation.domain.services import (
    CausalAppraiser,
    ContradictionDetector,
    FigureComparison,
    ResolveMeasureIdentity,
)


def test_application_services_own_use_cases() -> None:
    for service in (
        VerifyClaim,
        FlagUnsupportedAssertion,
        GetClaim,
        RegisterReferenceFigure,
        ListReferenceFigures,
        ListContradictions,
        ResolveExpertReview,
    ):
        assert service.__module__ == "claim_validation.application.services"
        assert "execute" in method_names(service)


def test_domain_services_own_pure_rules() -> None:
    assert ResolveMeasureIdentity.__module__ == "claim_validation.domain.services"
    assert FigureComparison.__module__ == "claim_validation.domain.services"
    assert ContradictionDetector.__module__ == "claim_validation.domain.services"
    assert CausalAppraiser.__module__ == "claim_validation.domain.services"
    assert "resolve" in method_names(ResolveMeasureIdentity)
    assert "compare" in method_names(FigureComparison)
