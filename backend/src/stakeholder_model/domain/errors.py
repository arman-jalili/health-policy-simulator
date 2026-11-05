"""Frozen error contract of the StakeholderModel context (ADR-004).

Canonical: .pi/architecture/modules/stakeholder-model.md

Codes are stable machine identifiers; the API envelope never depends on message wording.
"""

from __future__ import annotations

from shared.errors import NotFoundError, ValidationFailedError


class PersonRepresentationForbidden(ValidationFailedError):
    """An institution was represented by, or named after, a natural person (invariant 1)."""

    code = "PERSON_REPRESENTATION_FORBIDDEN"

    def __init__(self, identity_name: str) -> None:
        super().__init__(
            f"stakeholder {identity_name!r} is a natural person; only institutions may negotiate"
        )


class IncompleteProfile(ValidationFailedError):
    """A profile cannot be activated without at least one interest and one constraint."""

    code = "INCOMPLETE_PROFILE"

    def __init__(self, stakeholder_id: str, missing: tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__(
            f"stakeholder {stakeholder_id} cannot be activated; missing {', '.join(missing)}"
        )


class UnsourcedAuthority(ValidationFailedError):
    """A power claim was refused because it cites no admissible instrument (invariant 8)."""

    code = "UNSOURCED_AUTHORITY"

    def __init__(self, stakeholder_id: str, power_type: str) -> None:
        self.power_type = power_type
        super().__init__(f"stakeholder {stakeholder_id} cannot claim {power_type} without a source")


class VetoNarrowedToProposal(ValidationFailedError):
    """A veto applies to a proposal class, never to one proposal id (invariant 7)."""

    code = "VETO_NARROWED_TO_PROPOSAL"

    def __init__(self, proposal_id: str) -> None:
        self.proposal_id = proposal_id
        super().__init__(f"veto cannot be narrowed to proposal {proposal_id}; declare a class")


class BindingIncomplete(ValidationFailedError):
    """An AgentBinding lacks the identity or persona needed to bind an agent."""

    code = "BINDING_INCOMPLETE"


class StakeholderNotFound(NotFoundError):
    """The requested institution is not registered."""

    code = "STAKEHOLDER_NOT_FOUND"

    def __init__(self, stakeholder_id: str) -> None:
        super().__init__(f"stakeholder {stakeholder_id} not found")


class AgentBindingNotFound(NotFoundError):
    """No binding exists for the requested run/institution pair."""

    code = "AGENT_BINDING_NOT_FOUND"

    def __init__(self, run_id: str, stakeholder_id: str) -> None:
        super().__init__(f"no agent binding for run {run_id} and stakeholder {stakeholder_id}")
