"""FastAPI dependency guard: resolve a principal, enforce its scope, bind the actor.

Canonical: .pi/architecture/modules/identity-access.md

Strict mode never defaults to anonymous: a missing or unknown key is a 401 with the uniform
envelope. The resolved principal's label is bound through ``actor_scope`` for the request, so every
command event written by an outbox publisher carries the actor (ADR-005, ADR-006).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import cast

from fastapi import Request

from identity_access.interfaces.demo import demo_principal, is_loopback_host
from identity_access.interfaces.errors import (
    AuthenticationRequiredError,
    InsufficientScopeError,
)
from identity_access.interfaces.ports import PrincipalPort
from identity_access.interfaces.types import Principal, Scope
from shared.attribution import actor_scope
from shared.errors import ErrorDetail
from shared.http.deps import get_app_settings

PrincipalDependency = Callable[..., AsyncIterator[Principal]]


async def _resolve_principal(request: Request) -> Principal:
    settings = get_app_settings(request)

    if settings.is_demo:
        host = request.client.host if request.client is not None else None
        if not is_loopback_host(host):
            raise AuthenticationRequiredError("Demo mode is only available from localhost")
        return demo_principal()

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise AuthenticationRequiredError("Missing X-API-Key header")

    container = getattr(request.app.state, "identity_access", None)
    principal_port = (
        cast(PrincipalPort | None, getattr(container, "principal_port", None))
        if container is not None
        else None
    )
    if principal_port is None:
        raise AuthenticationRequiredError("No API key store is configured")
    return await principal_port.resolve(api_key)


@asynccontextmanager
async def _authorized(request: Request, required_scope: Scope) -> AsyncIterator[Principal]:
    principal = await _resolve_principal(request)
    if not principal.has_scope(required_scope):
        raise InsufficientScopeError(
            f"Missing required scope: {required_scope.value}",
            details=[
                ErrorDetail(
                    message="required scope",
                    field="scope",
                    code=required_scope.value,
                )
            ],
        )
    with actor_scope(principal.actor_id()):
        yield principal


def require_scope(scope: Scope) -> PrincipalDependency:
    """Build the per-route dependency that resolves a principal and enforces ``scope``."""

    async def dependency(request: Request) -> AsyncIterator[Principal]:
        async with _authorized(request, scope) as principal:
            yield principal

    return dependency


async def require_declared_scope(request: Request) -> AsyncIterator[Principal]:
    """Enforce the scope declared by the matched route as ``x-required-scope``.

    Routers attach this once and keep the declaration beside each handler, so a new route cannot
    silently opt out of authentication.
    """
    route = request.scope.get("route")
    openapi_extra = getattr(route, "openapi_extra", None) or {}
    declared = openapi_extra.get("x-required-scope")
    if not isinstance(declared, str) or not declared:
        raise InsufficientScopeError("Route does not declare a required scope")
    async with _authorized(request, Scope(declared)) as principal:
        yield principal
