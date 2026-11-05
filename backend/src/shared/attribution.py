"""Request-scoped actor attribution (ADR-005, ADR-006).

Canonical: .pi/architecture/modules/identity-access.md

The auth dependency opens an actor scope for the duration of the request; every outbox writer reads
it so command events carry the resolved principal's label. Background work without a scope keeps
its explicit actor (``system``), so attribution never silently becomes empty.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_current_actor: ContextVar[str | None] = ContextVar("current_actor", default=None)


def current_actor() -> str | None:
    """Return the actor bound to the current request/task, if any."""
    return _current_actor.get()


@contextmanager
def actor_scope(actor: str) -> Iterator[None]:
    """Bind a non-empty actor for the duration of the context."""
    normalized = actor.strip()
    if not normalized:
        raise ValueError("actor must be non-empty")
    token = _current_actor.set(normalized)
    try:
        yield
    finally:
        _current_actor.reset(token)
