"""Identifier generation for every aggregate, event and row.

Canonical: .pi/architecture/implementation-roadmap.md (Phase 0 — shared kernel)

Identifiers are ULIDs with a type prefix (``doc_01J...``): lexicographically sortable by
creation time, collision-resistant, and self-describing in logs, event payloads and URLs.

Canonical: .pi/architecture/implementation-roadmap.md (Phase 0 - shared kernel)
"""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ULID_LENGTH = 26
_PREFIX_PATTERN = re.compile(r"^[a-z][a-z0-9]{0,15}$")
_ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def new_ulid(moment: datetime | None = None) -> str:
    """Return a 26-character ULID for ``moment`` (defaults to now, UTC)."""
    moment = moment or datetime.now(tz=UTC)
    if moment.tzinfo is None:
        raise ValueError("new_ulid() requires a timezone-aware datetime")
    timestamp_ms = int(moment.astimezone(UTC).timestamp() * 1000)
    if not 0 <= timestamp_ms < 1 << 48:
        raise ValueError("timestamp out of ULID range")

    value = (timestamp_ms << 80) | secrets.randbits(80)
    chars = []
    for _ in range(ULID_LENGTH):
        value, remainder = divmod(value, 32)
        chars.append(CROCKFORD32[remainder])
    return "".join(reversed(chars))


def new_id(prefix: str, moment: datetime | None = None) -> str:
    """Return a prefixed identifier, e.g. ``new_id("doc") -> "doc_01J..."``."""
    if not _PREFIX_PATTERN.match(prefix):
        raise ValueError(
            f"invalid id prefix {prefix!r}: expected lowercase alphanumeric, 1-16 chars, "
            "starting with a letter"
        )
    return f"{prefix}_{new_ulid(moment)}"


def is_ulid(value: str) -> bool:
    """Return True when ``value`` is a syntactically valid ULID."""
    return bool(_ULID_PATTERN.match(value))


def is_id(value: str, prefix: str | None = None) -> bool:
    """Return True when ``value`` is a prefixed ULID, optionally of a specific ``prefix``."""
    head, separator, ulid = value.partition("_")
    if not separator or not _PREFIX_PATTERN.match(head) or not is_ulid(ulid):
        return False
    return prefix is None or head == prefix


def split_id(value: str) -> tuple[str, str]:
    """Split ``prefix_ulid`` into ``(prefix, ulid)``; raise ``ValueError`` when malformed."""
    head, separator, ulid = value.partition("_")
    if not separator or not _PREFIX_PATTERN.match(head) or not is_ulid(ulid):
        raise ValueError(f"malformed identifier: {value!r}")
    return head, ulid
