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


# --- behaviour: layer boundaries (issue #167) ------------------------------------------------

from tests.unit.claim_validation_contract_helpers import imported_names  # noqa: E402

from claim_validation.domain.claim import Claim  # noqa: E402
from claim_validation.infrastructure.number_parser import GermanNumberParser  # noqa: E402
from claim_validation.interfaces.http.router import router  # noqa: E402


def test_aggregate_is_domain_owned() -> None:
    assert Claim.__module__ == "claim_validation.domain.claim"


def test_text_parsing_is_an_infrastructure_adapter() -> None:
    assert GermanNumberParser.__module__ == "claim_validation.infrastructure.number_parser"


def test_http_router_is_the_interface_layer() -> None:
    assert router.prefix == "/api/v1"
    assert "claim-validation" in (router.tags or [])


def test_application_layer_never_imports_infrastructure() -> None:
    from pathlib import Path

    application = Path("src/claim_validation/application")
    for module in application.glob("*.py"):
        imports = imported_names(module)
        forbidden = [name for name in imports if name.startswith("claim_validation.infrastructure")]
        assert not forbidden, module
