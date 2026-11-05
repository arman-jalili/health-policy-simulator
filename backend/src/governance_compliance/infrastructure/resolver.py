"""Institutional alias resolver over the published allowlist (GC-003)."""

from __future__ import annotations

from governance_compliance.application.values import InstitutionalAllowlist


class AllowlistInstitutionResolver:
    def resolve(self, mention: str, allowlist: InstitutionalAllowlist) -> str | None:
        return allowlist.aliases.get(mention.strip())
