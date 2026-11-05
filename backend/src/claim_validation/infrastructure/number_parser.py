"""German number extraction adapter (contract frozen, issue #164)."""

from __future__ import annotations

from decimal import Decimal


class GermanNumberParser:
    """Parse `1.204`, `3,2 Mrd. €`, `22 %` into a decimal value and unit."""

    def parse(self, text: str) -> tuple[Decimal, str] | None:
        raise NotImplementedError("implemented by issue #176")
