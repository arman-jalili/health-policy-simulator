"""Institutional alias resolver over the published allowlist (GC-003)."""

from __future__ import annotations

from governance_compliance.application.values import InstitutionalAllowlist


class AllowlistInstitutionResolver:
    def resolve(self, mention: str, allowlist: InstitutionalAllowlist) -> str | None:
        wanted = mention.strip().casefold()
        for alias, canonical in allowlist.aliases.items():
            if alias.casefold() == wanted:
                return canonical
        return None
