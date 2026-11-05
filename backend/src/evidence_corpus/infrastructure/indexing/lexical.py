"""Shared lexical query semantics for the memory and PostgreSQL index adapters.

Canonical: `.pi/architecture/modules/evidence-retrieval.md` (Invariant 3: adapter parity)

The German query rewrite emits ``A OR B OR C``. Both adapters must interpret that string the same
way, and both must treat expanded terms as prefixes so ``Kasse`` can find
``Kassenvertragsstellen``. Keeping the parsing here prevents the adapters from drifting again.
"""

from __future__ import annotations

import re
from typing import Final

_DISJUNCTION: Final[str] = " OR "
_TERM_NOISE = re.compile(r"[^\w]+", re.UNICODE)
_TOKEN = re.compile(r"\w+", re.UNICODE)


def is_disjunctive(query: str) -> bool:
    """Return whether the rewrite joined alternatives with ``OR``."""
    return _DISJUNCTION in query


def query_terms(query: str) -> tuple[str, ...]:
    """Return unique, case-folded terms with syntax noise removed, preserving order."""
    raw_terms = query.split(_DISJUNCTION) if is_disjunctive(query) else query.split()
    terms: list[str] = []
    seen: set[str] = set()
    for raw in raw_terms:
        term = _TERM_NOISE.sub("", raw).casefold()
        if term and term not in seen:
            seen.add(term)
            terms.append(term)
    return tuple(terms)


def text_tokens(text: str) -> tuple[str, ...]:
    """Tokenise passage text for prefix matching in the in-memory adapter."""
    return tuple(token.casefold() for token in _TOKEN.findall(text))


def term_prefix_matches(term: str, tokens: tuple[str, ...]) -> bool:
    """Return whether any token starts with ``term`` (the Postgres ``term:*`` equivalent)."""
    return any(token.startswith(term) for token in tokens)
