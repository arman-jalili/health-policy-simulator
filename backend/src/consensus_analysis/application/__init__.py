"""Application layer of ConsensusAnalysis: use cases over the derived projections.

Each service is one transaction boundary and one use case. Business rules stay in the aggregates
and domain services; these modules orchestrate loading, rule evaluation, persistence and events.
"""

from __future__ import annotations

__all__: list[str] = []
