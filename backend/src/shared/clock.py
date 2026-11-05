"""Time handling: one injectable clock, UTC only, ISO-8601 on the wire (ADR-004).

Canonical: .pi/architecture/decisions/ADR-004-api-design.md (time handling)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable


def utcnow() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(tz=UTC)


def iso_z(moment: datetime) -> str:
    """Render ``moment`` as ISO-8601 UTC with a ``Z`` suffix and millisecond precision."""
    if moment.tzinfo is None:
        raise ValueError("iso_z() requires a timezone-aware datetime")
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@runtime_checkable
class Clock(Protocol):
    """Port for reading the current time; injected so domain logic stays deterministic."""

    def now(self) -> datetime: ...


class SystemClock:
    """Production clock backed by the operating system."""

    def now(self) -> datetime:
        return utcnow()

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return "SystemClock()"


class FixedClock:
    """Test clock: returns ``moment`` until :meth:`advance` is called."""

    __slots__ = ("_moment",)

    def __init__(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._moment = moment.astimezone(UTC)

    def now(self) -> datetime:
        return self._moment

    def advance(self, seconds: float = 0.0, days: float = 0.0) -> datetime:
        from datetime import timedelta

        if seconds < 0 or days < 0:
            raise ValueError("FixedClock only moves forward")
        self._moment = self._moment + timedelta(seconds=seconds, days=days)
        return self._moment

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"FixedClock({self._moment.isoformat()})"
