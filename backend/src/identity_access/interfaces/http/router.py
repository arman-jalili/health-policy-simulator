"""Concrete admin router for API-key lifecycle (ADR-004, ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Routes are frozen here; the lifecycle is implemented against ``ApiKeyAdminPort``. The composition
root (issue #41) mounts this router and binds the adapter on ``app.state.identity_access``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from identity_access.interfaces.dto import CreateApiKeyCommand
from identity_access.interfaces.http.dependencies import require_scope
from identity_access.interfaces.http.deps import get_api_key_admin
from identity_access.interfaces.http.schemas import (
    ApiKeySummaryResponse,
    CreateApiKeyRequest,
    IssuedApiKeyResponse,
)
from identity_access.interfaces.ports import ApiKeyAdminPort
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
    admin: Annotated[ApiKeyAdminPort, Depends(get_api_key_admin)],
    principal: Annotated[Principal, Depends(require_scope(Scope.ADMIN))],
) -> IssuedApiKeyResponse:
    """Issue a key and return the plaintext exactly once."""
    issued = await admin.create_key(CreateApiKeyCommand(label=payload.label, role=payload.role))
    return IssuedApiKeyResponse(
        key_id=issued.key_id,
        key=issued.key,
        label=issued.label,
        role=issued.role,
        created_at=issued.created_at,
    )


@router.get(
    "/keys",
    response_model=list[ApiKeySummaryResponse],
    responses=ADMIN_ERRORS,
    openapi_extra={"x-required-scope": Scope.ADMIN.value},
)
async def list_api_keys(
    admin: Annotated[ApiKeyAdminPort, Depends(get_api_key_admin)],
    principal: Annotated[Principal, Depends(require_scope(Scope.ADMIN))],
) -> list[ApiKeySummaryResponse]:
    """List key metadata without hashes or plaintext."""
    summaries = await admin.list_keys()
    return [
        ApiKeySummaryResponse(
            key_id=summary.key_id,
            label=summary.label,
            role=summary.role,
            created_at=summary.created_at,
            revoked_at=summary.revoked_at,
        )
        for summary in summaries
    ]


@router.delete(
    "/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=ADMIN_ERRORS,
    openapi_extra={"x-required-scope": Scope.ADMIN.value},
)
async def revoke_api_key(
    key_id: str,
    admin: Annotated[ApiKeyAdminPort, Depends(get_api_key_admin)],
    principal: Annotated[Principal, Depends(require_scope(Scope.ADMIN))],
) -> None:
    """Revoke a key; the next request with it must fail with 401."""
    await admin.revoke_key(key_id)
