"""Identifier contract: prefixed, sortable, unique, validated."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from shared.ids import is_id, is_ulid, new_id, new_ulid, split_id


def test_new_id_carries_prefix_and_valid_ulid() -> None:
    identifier = new_id("doc")

    prefix, ulid = identifier.split("_")
    assert prefix == "doc"
    assert len(ulid) == 26
    assert is_ulid(ulid)
    assert is_id(identifier, "doc")


def test_ids_sort_by_creation_time() -> None:
    earlier = datetime(2026, 11, 5, 9, 0, tzinfo=UTC)
    later = earlier + timedelta(seconds=1)

    assert new_ulid(earlier) < new_ulid(later)


def test_ids_are_unique_within_a_millisecond() -> None:
    moment = datetime(2026, 11, 5, 9, 0, tzinfo=UTC)
    generated = {new_ulid(moment) for _ in range(250)}

    assert len(generated) == 250


@pytest.mark.parametrize("prefix", ["", "Doc", "1doc", "doc-dash", "a" * 17])
def test_invalid_prefixes_are_rejected(prefix: str) -> None:
    with pytest.raises(ValueError, match="invalid id prefix"):
        new_id(prefix)


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        new_ulid(datetime(2026, 11, 5, 9, 0))


def test_prefix_mismatch_is_not_a_match() -> None:
    identifier = new_id("doc")

    assert not is_id(identifier, "evt")


@pytest.mark.parametrize("value", ["", "doc", "doc_", "doc_short", "_" + "0" * 26, "x" * 26])
def test_malformed_identifiers_are_rejected(value: str) -> None:
    assert not is_id(value)
    with pytest.raises(ValueError, match="malformed identifier"):
        split_id(value)


def test_split_id_round_trips() -> None:
    identifier = new_id("run")

    prefix, ulid = split_id(identifier)

    assert prefix == "run"
    assert is_ulid(ulid)
