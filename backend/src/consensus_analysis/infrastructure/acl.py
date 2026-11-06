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
from consensus_analysis.domain.values import DocumentedExample, ProposalClass
from stakeholder_model.interfaces.published import StakeholderProfileView


class StakeholderPowersAcl:
    """Map the partner profile contract to the domain veto vocabulary."""

    def to_veto_classes(self, profile: StakeholderProfileView) -> frozenset[ProposalClass]:
        """Return the classes this institution may block; an empty set is not "no veto record"."""
        raise NotImplementedError(
            "StakeholderPowersAcl.to_veto_classes is implemented by issue #309"
        )


class ReferenceFigureAcl:
    """Map a ClaimValidation verdict to an enumerable derivation input, or to nothing."""

    def to_reference_figure(self, verdict: ClaimVerdictView) -> ReferenceFigureView | None:
        """Return the figure when the verdict carries a verified delta, otherwise ``None``."""
        raise NotImplementedError(
            "ReferenceFigureAcl.to_reference_figure is implemented by issue #313"
        )


class IllustrativeExampleCatalog:
    """The documentation example catalogue the illustrative-value guard refuses (invariant 8)."""

    def __init__(self, *, examples: Sequence[DocumentedExample]) -> None:
        self._examples = tuple(examples)

    def examples(self) -> Sequence[DocumentedExample]:
        """Return every documented example value; the guard owns the comparison rule."""
        return self._examples
