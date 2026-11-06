"""Views published to other contexts (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Dependencies, Context Map)

DecisionBrief consumes :class:`ConsensusView` and the published events; the relationship is
conformist, so this shape is the brief's model. Every view is derived and read-only: an id plus the
facts a brief needs, never a repository, ORM or session type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MinorityPositionView:
    holders: tuple[str, ...]
    objections: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConsensusRecordView:
    """One derived topic outcome as downstream contexts read it."""

    consensus_id: str
    topic: str
    proposal_class: str
    outcome: str
    support: float
    threshold: float
    supporters: tuple[str, ...] = ()
    minorities: tuple[MinorityPositionView, ...] = ()
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class UnresolvedConflictView:
    topic: str
    holders: tuple[str, ...] = ()
    positions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PackageComponentView:
    component_id: str
    measure: str
    accepted_by: tuple[str, ...] = ()
    cost_eur: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CompromisePackageView:
    package_id: str
    state: str
    components: tuple[PackageComponentView, ...] = ()
    rejected_measures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EstimatedFigureView:
    field: str
    value: Decimal
    basis: str
    label: str
    limitation: str | None = None


@dataclass(frozen=True, slots=True)
class ImpactAssessmentView:
    scenario_id: str
    package_id: str
    baseline: str
    horizon_years: int
    figures: tuple[EstimatedFigureView, ...] = ()
    political: str = "unknown"
    legal: str = "unknown"
    administrative: str = "unknown"


@dataclass(frozen=True, slots=True)
class ComparisonEntryView:
    package_id: str
    scenario_id: str
    cost: Decimal | None
    acceptance: float
    political: str
    legal: str
    administrative: str
    rank: int


@dataclass(frozen=True, slots=True)
class ConsensusView:
    """The whole derived result of one run, as the DecisionBrief projects it."""

    run_id: str
    records: tuple[ConsensusRecordView, ...] = field(default_factory=tuple)
    unresolved: tuple[UnresolvedConflictView, ...] = field(default_factory=tuple)
    packages: tuple[CompromisePackageView, ...] = field(default_factory=tuple)
    assessments: tuple[ImpactAssessmentView, ...] = field(default_factory=tuple)
    comparison: tuple[ComparisonEntryView, ...] = field(default_factory=tuple)
