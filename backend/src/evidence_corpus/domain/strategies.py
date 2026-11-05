"""Article boundary strategies (domain service implementations).

Canonical: .pi/architecture/modules/evidence-corpus.md

Two real variants: a press PDF is usually one editorial unit, while a clipping digest contains
several clippings. The digest format is explicit so segmentation is deterministic and reviewable:
clippings are separated by a line of three or more hyphens, the first non-empty line of a clipping
is its headline, and each clipping is its own clipping unit (page 1, 2, 3, ... in digest order).
"""

from __future__ import annotations

import re

from evidence_corpus.domain.entities import Publication
from evidence_corpus.domain.values import ArticleDraft

FORM_FEED = "\f"
_CLIPPING_SEPARATOR = re.compile(r"(?m)^-{3,}\s*$")
_MAX_HEADLINE_LENGTH = 200


class SingleArticleStrategy:
    """One document is one editorial unit (the common case for a press PDF)."""

    def segment(self, text: str, publication: Publication) -> list[ArticleDraft]:
        pages = [page.strip() for page in text.split(FORM_FEED)]
        _assert_segmentable(text)

        headline, body = _split_headline(text)
        return [
            ArticleDraft(
                headline=headline,
                body=body,
                page_from=1,
                page_to=max(1, len(pages)),
            )
        ]


class ClippingDigestStrategy:
    """A digest page contains several clippings that must become distinct articles."""

    def segment(self, text: str, publication: Publication) -> list[ArticleDraft]:
        _assert_segmentable(text)

        drafts: list[ArticleDraft] = []
        for page, (_start, block) in enumerate(_clipping_blocks(text), start=1):
            headline, body = _split_headline(block)
            drafts.append(
                ArticleDraft(
                    headline=headline,
                    body=body,
                    page_from=page,
                    page_to=page,
                )
            )
        return drafts


def select_strategy(text: str) -> SingleArticleStrategy | ClippingDigestStrategy:
    """Pick the digest strategy only when the document actually marks clipping boundaries."""
    return ClippingDigestStrategy() if _CLIPPING_SEPARATOR.search(text) else SingleArticleStrategy()


def _clipping_blocks(text: str) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    position = 0
    for match in _CLIPPING_SEPARATOR.finditer(text):
        blocks.append((position, text[position : match.start()]))
        position = match.end()
    blocks.append((position, text[position:]))

    return [
        (start + _leading_whitespace_length(block), block.strip())
        for start, block in blocks
        if block.strip()
    ]


def _leading_whitespace_length(block: str) -> int:
    return len(block) - len(block.lstrip())


def _assert_segmentable(text: str) -> None:
    if not text.strip():
        raise ValueError("cannot segment an empty document")


def _split_headline(block: str) -> tuple[str, str]:
    lines = [line.strip() for line in block.lstrip().splitlines()]
    non_empty = [line for line in lines if line]
    if not non_empty:
        raise ValueError("cannot segment an empty clipping")

    headline = non_empty[0][:_MAX_HEADLINE_LENGTH]
    body = block.lstrip().split("\n", 1)[1].strip() if len(lines) > 1 else ""
    if not body:
        raise ValueError("clipping has a headline but no body")
    return headline, body
