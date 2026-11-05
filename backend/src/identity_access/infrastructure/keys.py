"""Key material generation and hashing (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Keys are high-entropy generated values embedded with their ``key_id`` prefix, then salted and
hashed with SHA-256. The plaintext is returned once; only ``key_hash``/``salt`` are persisted.
"""

from __future__ import annotations

import hashlib
import secrets

from identity_access.infrastructure.ports import KeyMaterial
from shared.ids import new_id

SECRET_BYTES = 32
SALT_BYTES = 16


def hash_key(secret: str, salt: str) -> str:
    """Return the salted SHA-256 hash of a key secret (hex)."""
    return hashlib.sha256(f"{salt}:{secret}".encode()).hexdigest()


class Sha256ApiKeyFactory:
    """Generate a prefixed key id, a high-entropy secret, and its salted hash."""

    def generate(self) -> KeyMaterial:
        key_id = new_id("key")
        secret = secrets.token_urlsafe(SECRET_BYTES)
        salt = secrets.token_hex(SALT_BYTES)
        return KeyMaterial(
            key_id=key_id,
            plaintext_key=f"{key_id}.{secret}",
            key_hash=hash_key(secret, salt),
            salt=salt,
        )
