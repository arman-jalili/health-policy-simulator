"""Key-store record: the vendor shape that never leaves ``infrastructure`` (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Hashes and salts are excluded from ``repr``. No module outside this package may import this type
(the ACL-isolation contract test enforces it).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from identity_access.interfaces.types import Role


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    """One persisted key: metadata plus the salted hash, never the plaintext."""

    key_id: str
    label: str
    role: Role
    key_hash: str = field(repr=False)
    salt: str = field(repr=False)
    created_at: datetime
    revoked_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
