"""IdentityAccess — API-key authentication, authorisation and attribution (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Adapter depth (ADR-008): no domain entities, aggregates or domain events. The frozen contract is the
narrow ACL in ``interfaces/``; ``infrastructure/`` supplies the adapters. ``domain/`` and
``application/`` exist only as empty layer markers because the DDD structure validator requires all
four directories while the modeling-depth validator forbids Python modules there.
"""

from __future__ import annotations
