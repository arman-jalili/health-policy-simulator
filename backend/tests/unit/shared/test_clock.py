"""Clock contract: UTC-only, ISO-8601 with ``Z``, deterministic under test."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from shared.clock import FixedClock, SystemClock, iso_z, utcnow


def test_utcnow_is_timezone_aware_utc() -> None:
    moment = utcnow()

    assert moment.tzinfo is not None
    assert moment.utcoffset() == timedelta(0)


def test_system_clock_matches_utcnow() -> None:
    assert SystemClock().now().tzinfo is not None


def test_iso_z_renders_utc_with_milliseconds() -> None:
    moment = datetime(2026, 11, 5, 9, 30, 15, 123456, tzinfo=UTC)

    assert iso_z(moment) == "2026-11-05T09:30:15.123Z"


def test_iso_z_converts_other_offsets_to_utc() -> None:
    moment = datetime(2026, 11, 5, 10, 30, tzinfo=timezone(timedelta(hours=1)))

    assert iso_z(moment) == "2026-11-05T09:30:00.000Z"


def test_iso_z_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        iso_z(datetime(2026, 11, 5, 9, 30))


def test_fixed_clock_advances_forward_only(fixed_clock: FixedClock) -> None:
    start = fixed_clock.now()

    fixed_clock.advance(seconds=30)
    assert fixed_clock.now() == start + timedelta(seconds=30)

    with pytest.raises(ValueError, match="forward"):
        fixed_clock.advance(seconds=-1)


def test_fixed_clock_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FixedClock(datetime(2026, 11, 5, 9, 30))
