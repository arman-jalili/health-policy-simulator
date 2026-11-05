"""Read use case for the corpus-owned authority rubric."""

from __future__ import annotations

from evidence_corpus.application.commands import ListAuthorityRulesRequest
from evidence_corpus.application.dto import AuthorityRuleView
from evidence_corpus.domain.repositories import AuthorityRuleRepository
from evidence_corpus.domain.values import AuthorityTier


class ListAuthorityRulesHandler:
    """Implements :class:`evidence_corpus.application.services.ListAuthorityRules`."""

    def __init__(self, rules: AuthorityRuleRepository) -> None:
        self._rules = rules

    async def execute(self, request: ListAuthorityRulesRequest) -> list[AuthorityRuleView]:
        rules = (
            [await self._rules.for_claim_type(request.claim_type)]
            if request.claim_type is not None
            else await self._rules.list_all()
        )
        return [
            AuthorityRuleView(
                claim_type=rule.claim_type,
                ordered_tiers=[AuthorityTier(source.value) for source in rule.ordered_source_types],
            )
            for rule in rules
        ]
