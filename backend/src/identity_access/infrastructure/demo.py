"""Concrete demo-mode policy (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

The policy is deliberately tiny: loopback detection lives in the interfaces demo module so the
HTTP guard can use it without importing infrastructure. Composition (issue #41) binds this class
to ``IdentityAccessContainer.demo_policy``.
"""

from __future__ import annotations

from identity_access.interfaces.demo import is_loopback_host


class LoopbackDemoPolicy:
    """Permit demo principals only from loopback clients."""

    def permits(self, client_host: str | None) -> bool:
        return is_loopback_host(client_host)
