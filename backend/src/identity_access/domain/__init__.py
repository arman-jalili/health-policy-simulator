"""Empty marker: IdentityAccess has no domain model (ADR-008, adapter depth).

Canonical: .pi/architecture/modules/identity-access.md

Do not add entities, aggregates, value objects or domain events here. The capability is generic;
its only published concept is the ACL ``Principal`` in ``identity_access.interfaces``.
"""

from __future__ import annotations
