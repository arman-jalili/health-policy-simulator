"""Contract freeze: API, published language and ACL boundary (issue #164)."""

from __future__ import annotations

from fastapi import FastAPI
from tests.unit.claim_validation_contract_helpers import (
    SRC,
    field_names,
    imported_names,
)

from claim_validation.interfaces.http.deps import ClaimValidationContainer
from claim_validation.interfaces.http.router import router
from claim_validation.interfaces.published import ClaimVerdictView


def test_routes_are_frozen_with_scopes() -> None:
    app = FastAPI()
    app.include_router(router)
    paths = app.openapi()["paths"]

    expected = {
        "/api/v1/claims:verify": "runs:write",
        "/api/v1/claims/{claim_id}:flag": "runs:write",
        "/api/v1/claims/{claim_id}": "runs:read",
        "/api/v1/reference-figures": "corpus:write",
        "/api/v1/contradictions": "runs:read",
        "/api/v1/claims/{claim_id}/reviews": "admin",
    }
    for path, scope in expected.items():
        operations = [op for method in ("get", "post") if (op := paths[path].get(method))]
        assert operations, path
        assert any(op["x-required-scope"] == scope for op in operations), path


def test_published_view_contains_no_internal_state() -> None:
    assert field_names(ClaimVerdictView) == [
        "claim_id",
        "verdict",
        "claim_type",
        "sources",
        "delta",
    ]


def test_domain_and_application_do_not_import_repository_adapters() -> None:
    for layer in ("domain", "application"):
        for module in (SRC / layer).glob("*.py"):
            imports = imported_names(module)
            assert not any("infrastructure" in name for name in imports), module


def test_container_lists_every_http_use_case() -> None:
    annotations = ClaimValidationContainer.__annotations__
    assert set(annotations) == {
        "verify_claim",
        "flag_unsupported",
        "get_claim",
        "register_reference_figure",
        "list_reference_figures",
        "list_contradictions",
        "resolve_expert_review",
    }
