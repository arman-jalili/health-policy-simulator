"""Allowlist adapters: StakeholderModel published view -> guard allowlist."""

from __future__ import annotations

from governance_compliance.application.values import AllowlistEntry, InstitutionalAllowlist
from stakeholder_model.interfaces.published import InstitutionalAllowlistView


def from_published(view: InstitutionalAllowlistView) -> InstitutionalAllowlist:
    return InstitutionalAllowlist(
        institutions=tuple(
            AllowlistEntry(
                code=item.code,
                canonical_name=item.name,
                short_name=item.short_name,
                category=item.category.value,
            )
            for item in view.institutions
        )
    )


class StaticAllowlistSource:
    def __init__(self, allowlist: InstitutionalAllowlist) -> None:
        self._allowlist = allowlist

    def load(self) -> InstitutionalAllowlist:
        return self._allowlist
