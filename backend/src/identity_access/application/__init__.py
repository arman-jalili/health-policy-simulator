"""Empty marker: ADR-008 adapter depth forbids application modules.

Canonical: .pi/architecture/modules/identity-access.md

The narrow port and its DTOs live in ``identity_access.interfaces`` instead, because the
machine-readable modeling-depth projection allows only ``interfaces/`` and ``infrastructure/``
modules for adapter contexts. Keeping this directory empty satisfies the four-layer DDD structure
validator without violating ADR-008.
"""

from __future__ import annotations
