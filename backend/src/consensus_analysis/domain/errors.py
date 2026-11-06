"""Stable error codes of ConsensusAnalysis (contract frozen, issue #305).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Invariants)

Every failure that crosses the HTTP boundary renders as the uniform envelope
``{code, message, details, trace_id}`` (ADR-004). Each class names the invariant it protects and
the issue whose tests prove it.
"""

from __future__ import annotations

from collections.abc import Sequence

from shared.errors import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationFailedError,
)


class StanceNotInHistory(ValidationFailedError):
    """A stance that is absent from the closed run log was used (invariant 2, AC 3)."""

    code = "STANCE_NOT_IN_HISTORY"

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = tuple(missing)
        super().__init__(
            f"{len(self.missing)} stance(s) are not present in the closed run log",
            details=[
                {"message": "stance absent from the run log", "field": stakeholder}
                for stakeholder in self.missing
            ],
        )


class UnknownVetoClass(ValidationFailedError):
    """A veto right named a class this context cannot represent, so it cannot be evaluated (AC 1).

    Dropping it would silently restore consensus for a class an institution may block.
    """

    code = "UNKNOWN_VETO_CLASS"

    def __init__(self, value: str) -> None:
        self.value = value
        details = [{"message": "unknown proposal class in veto right", "field": "proposal_class"}]
        super().__init__(f"veto right names an unknown proposal class {value!r}", details=details)


class UnbackedEstimate(ValidationFailedError):
    """A figure claimed a computed basis without enumerating its inputs (invariant 7, AC 5)."""

    code = "UNBACKED_ESTIMATE"

    def __init__(self, field: str, claimed_basis: str, required: str = "assumed") -> None:
        self.field = field
        self.claimed_basis = claimed_basis
        super().__init__(
            f"figure {field!r} claims basis {claimed_basis!r} without enumerating its inputs; "
            f"without inputs the basis must be {required!r}",
            details=[
                {
                    "message": f"claim {claimed_basis!r} requires enumerated inputs",
                    "field": field,
                    "code": "UNBACKED_ESTIMATE",
                }
            ],
        )


class MislabeledEstimate(ValidationFailedError):
    """A figure's label disagrees with its basis (invariant 6, AC 6).

    The label is what a reader sees. A figure computed from a model but labelled "assumed", or an
    assumed figure labelled "evidenced", misrepresents its own provenance in either direction.
    """

    code = "MISLABELED_ESTIMATE"

    def __init__(self, field: str, basis: str, label: str, expected: str) -> None:
        self.field = field
        self.basis = basis
        self.label = label
        self.expected = expected
        super().__init__(
            f"figure {field!r} has basis {basis!r} but label {label!r}; "
            f"the honest label is {expected!r}",
            details=[
                {
                    "message": f"label must be {expected!r} for basis {basis!r}",
                    "field": field,
                    "code": "MISLABELED_ESTIMATE",
                }
            ],
        )


class IllustrativeValueRefused(ValidationFailedError):
    """A documentation example was presented as a run outcome (invariant 8, AC 7)."""

    code = "ILLUSTRATIVE_VALUE_REFUSED"


class FeasibilityContradictsVeto(ConflictError):
    """A scenario marked feasible names a veto holder as consenting (invariant 10, AC 10)."""

    code = "FEASIBILITY_CONTRADICTS_VETO"


class IncompatibleComponent(ConflictError):
    """Components accepted individually cannot be combined (invariant 5, AC 9)."""

    code = "INCOMPATIBLE_COMPONENT"


class PackageNotComposed(ConflictError):
    """An impact assessment was requested before the package was composed."""

    code = "PACKAGE_NOT_COMPOSED"


class ProjectionRebuildFailed(ConflictError):
    """A rebuild from the run log did not reproduce the persisted rows (AC 4)."""

    code = "PROJECTION_REBUILD_FAILED"


class ConsensusNotFound(NotFoundError):
    """No derived consensus record exists for the supplied id."""

    code = "CONSENSUS_NOT_FOUND"


class CompromisePackageNotFound(NotFoundError):
    """No compromise package exists for the supplied id."""

    code = "COMPROMISE_PACKAGE_NOT_FOUND"


class ScenarioNotFound(NotFoundError):
    """No scenario exists for the supplied id."""

    code = "SCENARIO_NOT_FOUND"


class ConsensusAnalysisUnavailable(ServiceUnavailableError):
    """A required collaborator is unbound; derivation fails closed, never invents agreement."""

    code = "CONSENSUS_ANALYSIS_UNAVAILABLE"
