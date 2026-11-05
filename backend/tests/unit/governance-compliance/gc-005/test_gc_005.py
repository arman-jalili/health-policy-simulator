"""GC-005 uses the real ClaimValidation verdict link."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, cast

from claim_validation.domain.claim import Claim
from claim_validation.domain.entities import ClaimVerification
from claim_validation.domain.values import (
    ClaimId,
    ClaimType,
    ReferenceFigureId,
    VerificationPath,
    VerificationVerdict,
)
from governance_compliance.application.rules import (
    ContradictedFigureRule,
    GuardRuleChain,
    context_for,
)
from governance_compliance.application.values import (
    GuardDecision,
    InstitutionalAllowlist,
    SpeakerKind,
)
from governance_compliance.infrastructure.figures import ClaimValidationFigureVerdicts


class _Claims:
    def __init__(self, claim: Claim) -> None:
        self._claim = claim

    async def all_claims(self) -> list[Claim]:
        return [self._claim]


def test_contradicted_reference_figure_is_rejected() -> None:
    claim = Claim(
        id=ClaimId("clm_1"),
        text="Die Kosten betragen 5 Mrd.",
        type=ClaimType.QUANTITATIVE,
        verdict=VerificationVerdict.CONTRADICTED,
        verification=ClaimVerification(
            verdict=VerificationVerdict.CONTRADICTED,
            path=VerificationPath.QUANTITATIVE,
            sources=("src_1",),
            method="figure comparison",
            reference_id=ReferenceFigureId("fig_x"),
            asserted_value=Decimal("5"),
            reference_value=Decimal("4"),
            delta=Decimal("1"),
        ),
    )
    chain = GuardRuleChain(
        [ContradictedFigureRule(ClaimValidationFigureVerdicts(cast(Any, _Claims(claim))))]
    )
    results = asyncio.run(
        chain.evaluate(
            context_for(
                text="Die Kosten betragen 5 Mrd.",
                speaker_kind=SpeakerKind.INSTITUTION,
                allowlist=InstitutionalAllowlist(),
                cited_passage_ids=(),
                reference_figure_ids=("fig_x",),
            )
        )
    )

    assert results[-1].decision is GuardDecision.REJECT
    assert results[-1].violation_class is not None
    assert results[-1].violation_class.value == "contradicted_figure"
