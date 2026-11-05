"""Institutional allowlist adapter published to GovernanceCompliance (ADR-007).

Canonical: .pi/architecture/modules/stakeholder-model.md

The source of truth for legitimate institutions is StakeholderModel. Until the governance context
is built, this adapter holds the published allowlist and is what its guard will consume.
"""

from __future__ import annotations

from collections.abc import Sequence

from shared.errors import ForbiddenError
from stakeholder_model.domain.values import InstitutionIdentity


class InstitutionNotAllowed(ForbiddenError):
    """An actor outside the published institutional allowlist attempted a run."""

    code = "INSTITUTION_NOT_ALLOWED"


class InstitutionalAllowlistGuard:
    """Recognises exactly the institutions published by StakeholderModel."""

    def __init__(self, identities: Sequence[InstitutionIdentity] = ()) -> None:
        self._codes: frozenset[str] = frozenset()
        if identities:
            self._codes = frozenset(identity.code for identity in identities)

    @property
    def codes(self) -> frozenset[str]:
        """Return the published institution codes."""
        return self._codes

    def recognises(self, code: str) -> bool:
        """Return whether ``code`` is in the published allowlist."""
        return code in self._codes

    async def assert_institution_only(self, identity: InstitutionIdentity) -> None:
        """Refuse persons and institutions outside the published allowlist."""
        if identity.is_person or not self.recognises(identity.code):
            raise InstitutionNotAllowed(
                f"institution {identity.code!r} is not in the published allowlist"
            )

    async def publish_allowlist(self, identities: Sequence[InstitutionIdentity]) -> None:
        """Replace the published allowlist with the given institutions."""
        self._codes = frozenset(identity.code for identity in identities)
