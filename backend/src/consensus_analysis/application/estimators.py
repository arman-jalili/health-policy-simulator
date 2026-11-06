"""Estimation strategies of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Patterns & OOP Mapping)

Four real bases, one interface, honest labels. The strategy that produced a figure is what makes the
label truthful: a measured figure cites a reference figure, a derived figure cites its inputs, a
modelled figure cites the metered invocation, and an assumed figure carries no computed pretence.
"""

from __future__ import annotations

from typing import ClassVar, Protocol, runtime_checkable

from consensus_analysis.application.dto import EstimateRequest
from consensus_analysis.application.ports import LlmImpactEstimator
from consensus_analysis.domain.values import BasisKind, EstimatedFigure


@runtime_checkable
class EstimateStrategy(Protocol):
    """One estimation basis; selection is a provenance decision, not a preference."""

    basis: ClassVar[BasisKind]

    async def estimate(self, request: EstimateRequest) -> EstimatedFigure: ...


class MeasuredEstimator:
    """A figure read from a verified reference figure (basis ``measured``)."""

    basis: ClassVar[BasisKind] = BasisKind.MEASURED

    async def estimate(self, request: EstimateRequest) -> EstimatedFigure:
        raise NotImplementedError("MeasuredEstimator.estimate is implemented by issue #313")


class DerivedEstimator:
    """A figure computed from enumerated inputs (basis ``derived``)."""

    basis: ClassVar[BasisKind] = BasisKind.DERIVED

    async def estimate(self, request: EstimateRequest) -> EstimatedFigure:
        raise NotImplementedError("DerivedEstimator.estimate is implemented by issue #313")


class ModelledEstimator:
    """A figure produced by the metered model client (basis ``modelled``, ADR-006)."""

    basis: ClassVar[BasisKind] = BasisKind.MODELLED

    def __init__(self, *, llm: LlmImpactEstimator) -> None:
        self._llm = llm

    def collaborators(self) -> tuple[object, ...]:
        """The metered model client this strategy requires (W8 reachability anchor)."""
        return (self._llm,)

    async def estimate(self, request: EstimateRequest) -> EstimatedFigure:
        raise NotImplementedError("ModelledEstimator.estimate is implemented by issue #313")


class AssumedEstimator:
    """A figure without enumerated inputs; publishable only with the assumed label (AC 6)."""

    basis: ClassVar[BasisKind] = BasisKind.ASSUMED

    async def estimate(self, request: EstimateRequest) -> EstimatedFigure:
        raise NotImplementedError("AssumedEstimator.estimate is implemented by issue #313")
