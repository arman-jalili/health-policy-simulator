"""German number extraction adapter (issue #176).

Canonical: `.pi/architecture/modules/claim-validation.md` (AC 9)

Parses German prose into a base value plus a unit: ``1.204`` -> 1204 count, ``3,2 Mrd. €`` ->
3_200_000_000 EUR, ``22 %`` -> 22 percent. Ambiguous text returns ``None`` instead of guessing.
"""

from __future__ import annotations

import re
from decimal import Decimal

_NUMBER = re.compile(r"\d[\d.,]*")
_SCALES = {
    "mrd": Decimal("1000000000"),
    "milliarden": Decimal("1000000000"),
    "mio": Decimal("1000000"),
    "millionen": Decimal("1000000"),
    "tsd": Decimal("1000"),
    "tausend": Decimal("1000"),
}


class GermanNumberParser:
    """Parse `1.204`, `3,2 Mrd. €`, `22 %` into a decimal value and unit."""

    def parse(self, text: str) -> tuple[Decimal, str] | None:
        matches = list(_NUMBER.finditer(text))
        if len(matches) != 1:
            # Refuse to guess: a year or a second figure may be the actual claim.
            return None
        match = matches[0]
        value = self._decimal(match.group(0))
        if value is None:
            return None
        window = " ".join(text[match.end() :].split()[:2]).casefold()
        scale = self._scale(window)
        unit = self._unit(window)
        if self._looks_like_year(match.group(0), value) and scale == 1 and unit == "count":
            return None
        return value * scale, unit

    @staticmethod
    def _looks_like_year(token: str, value: Decimal) -> bool:
        return token.isdigit() and len(token) == 4 and Decimal("1900") <= value <= Decimal("2099")

    @staticmethod
    def _decimal(token: str) -> Decimal | None:
        cleaned = token.rstrip(".,")
        if not cleaned or not any(character.isdigit() for character in cleaned):
            return None
        if "," in cleaned and "." in cleaned:
            last_comma = cleaned.rfind(",")
            last_dot = cleaned.rfind(".")
            if last_comma > last_dot:
                integer = cleaned[:last_comma].replace(".", "")
                fraction = cleaned[last_comma + 1 :]
            else:
                integer = cleaned[:last_dot].replace(",", "")
                fraction = cleaned[last_dot + 1 :]
            return _decimal(integer, fraction)
        if "," in cleaned:
            integer, _, fraction = cleaned.partition(",")
            return _decimal(integer, fraction)
        if "." in cleaned:
            groups = cleaned.split(".")
            if len(groups) > 2 or all(len(group) == 3 for group in groups[1:]):
                return _decimal("".join(groups), "")
            return _decimal(groups[0], groups[1])
        return _decimal(cleaned, "")

    @staticmethod
    def _scale(tail: str) -> Decimal:
        for marker, scale in _SCALES.items():
            if marker in tail:
                return scale
        return Decimal("1")

    @staticmethod
    def _unit(tail: str) -> str:
        if "%" in tail or "prozent" in tail:
            return "percent"
        if "€" in tail or "euro" in tail or "eur" in tail:
            return "EUR"
        return "count"


def _decimal(integer: str, fraction: str) -> Decimal | None:
    digits = integer + ("." + fraction if fraction else "")
    try:
        return Decimal(digits)
    except ArithmeticError:
        return None
