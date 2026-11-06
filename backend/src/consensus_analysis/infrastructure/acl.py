"""ACL adapters of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Dependencies, Wiring Contract)

These are the only places where an upstream published shape becomes a local value. The stakeholder
veto map arrives as ``StakeholderProfileView.veto_rights`` and leaves as
``frozenset[ProposalClass]``; a ClaimValidation verdict leaves as an enumerable reference figure.
No upstream module is imported by ``domain/``.
"""

from __future__ import annotations

from collections.abc import Sequence

from claim_validation.interfaces.published import ClaimVerdictView
from consensus_analysis.application.dto import ReferenceFigureView
from consensus_analysis.domain.errors import UnknownVetoClass
from consensus_analysis.domain.values import DocumentedExample, ProposalClass, ReferenceFigureId
from stakeholder_model.interfaces.published import StakeholderProfileView


class StakeholderPowersAcl:
    """Map the partner profile contract to the domain veto vocabulary."""

    def to_veto_classes(self, profile: StakeholderProfileView) -> frozenset[ProposalClass]:
        """Return the classes this institution may block.

        An empty set means the institution declared no blocking competence — never "veto rights
        were not loaded". An unrecognised class raises instead of being dropped, because dropping it
        would restore consensus for a class that can in fact be blocked (AC 1).
        """
        classes: set[ProposalClass] = set()
        for right in profile.veto_rights:
            value = str(right.proposal_class)
            try:
                classes.add(ProposalClass(value))
            except ValueError as error:
                raise UnknownVetoClass(value) from error
        return frozenset(classes)


class ReferenceFigureAcl:
    """Map a ClaimValidation verdict to an enumerable derivation input, or to nothing."""

    def to_reference_figure(self, verdict: ClaimVerdictView) -> ReferenceFigureView | None:
        """Return the figure when the verdict carries a verified delta, otherwise ``None``.

        A verdict without a delta resolved a claim but produced no number, so it cannot serve as a
        derivation input. Returning ``None`` is the honest answer: a measured basis without an input
        is exactly what ``EstimateValidator`` refuses.
        """
        if verdict.delta is None:
            return None
        return ReferenceFigureView(
            reference_figure_id=ReferenceFigureId(verdict.claim_id),
            value=verdict.delta,
            unit=verdict.claim_type,
            source=",".join(verdict.sources),
        )


class IllustrativeExampleCatalog:
    """The documentation example catalogue the illustrative-value guard refuses (invariant 8)."""

    def __init__(self, *, examples: Sequence[DocumentedExample]) -> None:
        self._examples = tuple(examples)

    def examples(self) -> Sequence[DocumentedExample]:
        """Return every documented example value; the guard owns the comparison rule."""
        return self._examples
