"""Demo-mode ACL values and the loopback predicate (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Demo mode is a localhost-only relaxation. Keeping the predicate and the demo principal in the
interfaces layer lets the HTTP dependency enforce it without importing infrastructure (ACL
isolation); ``infrastructure.demo.LoopbackDemoPolicy`` implements the same port for composition.
"""

from __future__ import annotations

from ipaddress import ip_address

from identity_access.interfaces.types import Principal, Role, Scope

_LOOPBACK_NAMES = frozenset({"localhost", "testclient"})


def is_loopback_host(host: str | None) -> bool:
    """Return true only for loopback addresses/names; unknown or missing hosts are not local."""
    if host is None:
        return False
    normalized = host.strip().lower()
    if not normalized:
        return False
    if normalized in _LOOPBACK_NAMES:
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def demo_principal() -> Principal:
    """The anonymous principal granted in demo mode.

    Known limitation: the demo principal currently carries every scope so the local corpus demo
    can write without provisioning a key. Narrowing to ADR-005's anonymous reads + ``runs:write``
    is a follow-up once the demo UI and keyed corpus tests are in place.
    """
    return Principal(label="demo", role=Role.ANALYST, scopes=frozenset(Scope), is_demo=True)
