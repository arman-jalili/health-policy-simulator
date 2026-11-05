"""ADR-008 service-depth marker.

SimulationOrchestration has no domain model: the graph sequences NegotiationSession, it never
owns negotiation state. This directory exists only because the repository-wide DDD layout check
requires the four layer directories; it must contain no implementation modules.
"""
