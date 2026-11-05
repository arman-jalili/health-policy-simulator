"""Ports consumed by the API layer and implemented by IdentityAccess infrastructure.

Canonical: .pi/architecture/modules/identity-access.md

The module is adapter depth (ADR-008): these are the only interfaces other layers depend on.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from identity_access.interfaces.dto import (
    ApiKeySummary,
    CreateApiKeyCommand,
    IssuedApiKey,
    ReadinessReport,
)
from identity_access.interfaces.types import Principal


@runtime_checkable
class PrincipalPort(Protocol):
    """Resolve a credential to an actor; the sole published concept (ADR-005)."""

    async def resolve(self, api_key: str | None) -> Principal:
        """Return the principal or raise ``AuthenticationRequiredError``.

        ``None`` is never a valid credential in strict mode. Demo mode is a different adapter, not
        a silent fallback.
        """
        ...


@runtime_checkable
class ApiKeyAdminPort(Protocol):
    """Admin lifecycle of API keys (key secrecy, listing, immediate revocation)."""

    async def create_key(self, command: CreateApiKeyCommand) -> IssuedApiKey:
        """Generate a key, persist only its hash, and return the plaintext exactly once."""
        ...

    async def list_keys(self) -> Sequence[ApiKeySummary]:
        """List key metadata without hashes or plaintext."""
        ...

    async def revoke_key(self, key_id: str) -> None:
        """Revoke a key so the next request fails with 401."""
        ...


@runtime_checkable
class ReadinessPort(Protocol):
    """Dependency probes reported by ``GET /readyz``."""

    async def check(self) -> ReadinessReport:
        """Return readiness for every registered dependency (DB, LLM)."""
        ...


@runtime_checkable
class DemoModePolicy(Protocol):
    """Localhost-only relaxation of strict authentication (ADR-005)."""

    def permits(self, client_host: str | None) -> bool:
        """Return true only for loopback clients while ``AUTH_MODE=demo``."""
        ...
