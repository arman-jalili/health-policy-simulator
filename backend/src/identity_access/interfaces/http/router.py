"""Concrete admin router for API-key lifecycle (ADR-004, ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Routes are frozen here; bodies are implemented by issues #36 (key secrecy) and #39 (revocation).
The router is deliberately not included in ``shared.app`` until issue #41 wires the context, so a
TODO body can never answer a real request.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from identity_access.interfaces.http.dependencies import require_scope
from identity_access.interfaces.http.schemas import (
    ApiKeySummaryResponse,
    CreateApiKeyRequest,
    IssuedApiKeyResponse,
)
from identity_access.interfaces.types import Principal, Scope
from shared.http.schemas import error_responses

ADMIN_ERRORS = error_responses(401, 403, 404, 422, 503)

router = APIRouter(prefix="/api/v1/admin", tags=["identity-access"])


@router.post(
    "/keys",
    status_code=status.HTTP_201_CREATED,
    response_model=IssuedApiKeyResponse,
    responses=ADMIN_ERRORS,
    openapi_extra={"x-required-scope": Scope.ADMIN.value},
)
async def create_api_key(
    payload: CreateApiKeyRequest,
    principal: Annotated[Principal, Depends(require_scope(Scope.ADMIN))],
) -> IssuedApiKeyResponse:
    """Issue a key and return the plaintext exactly once."""
    # TODO(issue #36): persist only the hash and return plaintext in this response.
    raise NotImplementedError("TODO(issue #36): issue an API key and return the plaintext once")


@router.get(
    "/keys",
    response_model=list[ApiKeySummaryResponse],
    responses=ADMIN_ERRORS,
    openapi_extra={"x-required-scope": Scope.ADMIN.value},
)
async def list_api_keys(
    principal: Annotated[Principal, Depends(require_scope(Scope.ADMIN))],
) -> list[ApiKeySummaryResponse]:
    """List key metadata without hashes or plaintext."""
    # TODO(issue #39): return the store's summaries.
    raise NotImplementedError("TODO(issue #39): list API keys without secrets")


@router.delete(
    "/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=ADMIN_ERRORS,
    openapi_extra={"x-required-scope": Scope.ADMIN.value},
)
async def revoke_api_key(
    key_id: str,
    principal: Annotated[Principal, Depends(require_scope(Scope.ADMIN))],
) -> None:
    """Revoke a key; the next request with it must fail with 401."""
    # TODO(issue #39): persist revoked_at and invalidate immediately.
    raise NotImplementedError("TODO(issue #39): revoke the API key immediately")
