"""Demo-mode ACL values and the loopback predicate (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Demo mode is a localhost-only relaxation. Keeping the predicate and the demo principal in the
interfaces layer lets the HTTP dependency enforce it without importing infrastructure (ACL
isolation); ``infrastructure.demo.LoopbackDemoPolicy`` implements the same port for composition.
"""

from __future__ import annotations

from collections.abc import Sequence
from ipaddress import ip_address, ip_network

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


def is_trusted_demo_host(host: str | None, trusted_cidrs: Sequence[str] = ()) -> bool:
    """Loopback, or a client inside an explicitly trusted network (containerised demos).

    ``AUTH_DEMO_TRUSTED_CIDRS`` is empty by default: demo mode stays loopback-only unless an
    operator names the networks, and the boot log plus ``/readyz`` report the setting so the
    relaxation is never invisible. Invalid entries are refused by the settings validator.
    """
    if is_loopback_host(host):
        return True
    if host is None or not trusted_cidrs:
        return False
    try:
        address = ip_address(host.strip())
    except ValueError:
        return False
    for cidr in trusted_cidrs:
        try:
            if address in ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def demo_principal() -> Principal:
    """The anonymous principal granted in demo mode.

    Known limitation: the demo principal currently carries every scope so the local corpus demo
    can write without provisioning a key. Narrowing to ADR-005's anonymous reads + ``runs:write``
    is a follow-up once the demo UI and keyed corpus tests are in place.
    """
    return Principal(label="demo", role=Role.ANALYST, scopes=frozenset(Scope), is_demo=True)
