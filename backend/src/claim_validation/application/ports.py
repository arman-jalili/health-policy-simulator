"""Application ports (contract frozen, issue #164; extended by #178)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal
from typing import Protocol

from claim_validation.domain.values import ClaimType, VerificationEvidence


class UnitOfWork(Protocol):
    def transaction(self) -> AsyncIterator[None]: ...


class Clock(Protocol):
    def today(self) -> date: ...


class NumberParserPort(Protocol):
    def parse(self, text: str) -> tuple[Decimal, str] | None: ...


class EvidencePort(Protocol):
    async def evidence_for(self, claim_type: ClaimType, text: str) -> VerificationEvidence: ...
