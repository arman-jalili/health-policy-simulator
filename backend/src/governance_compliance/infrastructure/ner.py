"""Deterministic title/name detector (GC-001). No model call on the guard path."""

from __future__ import annotations

import re
from collections.abc import Sequence

from governance_compliance.application.values import PersonReference, TextSpan

_TITLE = re.compile(
    r"\b(?:Dr\.|Mag\.|Prof\.|Dipl\.-Ing\.|Obmann|Obfrau|Präsident|Präsidentin)\s+"
    r"(?P<name>[A-ZÄÖÜ][\wÄÖÜäöüß-]+)"
)


class RegexPersonNameDetector:
    """Recognises honourific + surname patterns; intentionally deterministic."""

    def detect(self, text: str) -> Sequence[PersonReference]:
        return [
            PersonReference(
                text=match.group(0),
                span=TextSpan(match.start(), match.end()),
                title=match.group(0).split()[0],
            )
            for match in _TITLE.finditer(text)
        ]
