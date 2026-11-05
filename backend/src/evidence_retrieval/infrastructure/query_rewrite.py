"""Deterministic German query expansion for hybrid retrieval.

Canonical: .pi/architecture/modules/evidence-retrieval.md

The rewrite is vendor-free and reproducible from its input: no model call, no randomness. Compound
words are expanded into plausible parts so a lexical search can find "Kasse" when the claim says
"Kassenstellen"; the original term always stays first so exact matches keep priority.
"""

from __future__ import annotations

from evidence_retrieval.domain.values import QueryRewrite

MIN_COMPOUND_LENGTH = 10
MIN_PART_LENGTH = 5


class GermanQueryRewrite:
    """Expand German compounds and preserve the original query as the first term."""

    def rewrite(self, query: str) -> QueryRewrite:
        normalized = " ".join(query.split())
        if not normalized:
            raise ValueError("query must be non-empty")

        terms: list[str] = []
        seen: set[str] = set()
        for token in normalized.split():
            _append(terms, seen, token)
            if len(token) < MIN_COMPOUND_LENGTH:
                continue
            for split in range(MIN_PART_LENGTH, len(token) - MIN_PART_LENGTH + 1):
                left, right = token[:split], token[split:]
                _append(terms, seen, left)
                _append(terms, seen, right)

        return QueryRewrite(
            original=normalized,
            expanded=" OR ".join(terms),
        )


def _append(terms: list[str], seen: set[str], term: str) -> None:
    key = term.casefold()
    if key not in seen:
        seen.add(key)
        terms.append(term)
