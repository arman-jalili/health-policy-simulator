"""Application ports (contract frozen, issue #164)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from typing import Protocol

from claim_validation.domain.values import ClaimType, VerificationEvidence


class UnitOfWork(Protocol):
    def transaction(self) -> AsyncIterator[None]: ...


class Clock(Protocol):
    def today(self) -> date: ...


class EvidencePort(Protocol):
    async def evidence_for(self, claim_type: ClaimType, text: str) -> VerificationEvidence: ...
