"""Contract freeze: every command can name its actor from the resolved principal."""

from __future__ import annotations

import pytest

from identity_access.interfaces.types import Principal, Role, Scope


def test_principal_label_is_the_actor_id() -> None:
    principal = Principal(
        label="alice",
        role=Role.ANALYST,
        scopes=frozenset({Scope.RUNS_READ}),
    )

    assert principal.actor_id() == "alice"


def test_empty_actor_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="label"):
        Principal(label="   ", role=Role.ANALYST, scopes=frozenset())
