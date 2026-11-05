"""FastAPI dependency guard contract: every non-health route declares a scope.

Canonical: .pi/architecture/modules/identity-access.md

Issue #34 supplies the implementation. Until then the returned dependency raises a clear TODO
instead of silently allowing the request through.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request

from identity_access.interfaces.types import Principal, Scope

PrincipalDependency = Callable[..., Awaitable[Principal]]


def require_scope(scope: Scope) -> PrincipalDependency:
    """Build the per-route dependency that resolves a principal and enforces ``scope``."""

    async def dependency(request: Request) -> Principal:
        # TODO(issue #34): resolve via PrincipalPort and raise InsufficientScopeError instead.
        raise NotImplementedError(
            f"TODO(issue #34): resolve the principal and enforce {scope.value!r} "
            f"for {request.method} {request.url.path}"
        )

    return dependency
