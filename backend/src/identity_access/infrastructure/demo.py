"""Concrete demo-mode policy (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

The policy is deliberately tiny: loopback detection lives in the interfaces demo module so the
HTTP guard can use it without importing infrastructure. Composition (issue #41) binds this class
to ``IdentityAccessContainer.demo_policy``.
"""

from __future__ import annotations

from collections.abc import Sequence

from identity_access.interfaces.demo import is_trusted_demo_host


class LoopbackDemoPolicy:
    """Permit demo principals from loopback clients and explicitly trusted networks."""

    def __init__(self, trusted_cidrs: Sequence[str] = ()) -> None:
        self._trusted_cidrs = tuple(trusted_cidrs)

    def permits(self, client_host: str | None) -> bool:
        return is_trusted_demo_host(client_host, self._trusted_cidrs)
