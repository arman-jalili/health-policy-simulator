"""NegotiationSession — the negotiation state machine at the heart of the domain.

Canonical: ``.pi/architecture/modules/negotiation-session.md``
Modeling depth: tactical (core subdomain, ADR-008). One aggregate root (``SimulationRun``) owns
rounds, positions, arguments, conflicts, coalitions and learning; every invariant is enforced
inside one aggregate transaction.
"""
