"""Application layer: use-case services, DTOs and ports of NegotiationSession.

Services load the aggregate, call its guards and save through the frozen ports. They never
contain business rules — those live in ``domain/``.
"""
