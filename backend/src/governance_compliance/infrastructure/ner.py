"""Deterministic person detector (GC-001). No model call on the guard path."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from governance_compliance.application.values import PersonReference, TextSpan

_DEFAULT_NAMES = Path(__file__).resolve().parents[3] / "config" / "guard" / "person_names.txt"
_TITLE = re.compile(
    r"\b(?:Dr\.|Mag\.|Prof\.|Dipl\.-Ing\.|Obmann|Obfrau|Präsident|Präsidentin)\s+"
    r"(?P<name>[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]*)",
    re.IGNORECASE,
)


class RegexPersonNameDetector:
    """Titles, curated surnames, full names and initial+surname forms; deterministic."""

    def __init__(self, names: Sequence[str] | None = None) -> None:
        if names is None:
            names = _DEFAULT_NAMES.read_text(encoding="utf-8").splitlines()
        self._names = tuple(name.strip() for name in names if name.strip())
        surname = "|".join(re.escape(name) for name in sorted(self._names, key=len, reverse=True))
        self._surname = re.compile(rf"\b(?:[A-ZÄÖÜ]\.\s+)?(?:{surname})\b") if surname else None

    def detect(self, text: str) -> Sequence[PersonReference]:
        spans: list[tuple[int, int]] = [
            (match.start(), match.end()) for match in _TITLE.finditer(text)
        ]
        if self._surname is not None:
            spans.extend((match.start(), match.end()) for match in self._surname.finditer(text))
        merged: list[tuple[int, int]] = []
        for start, end in sorted(spans, key=lambda item: (item[0], -item[1])):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return [
            PersonReference(
                text=text[start:end],
                span=TextSpan(start, end),
                title=text[start:end].split()[0] if text[start:end] else None,
            )
            for start, end in merged
        ]
