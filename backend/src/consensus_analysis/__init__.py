"""ConsensusAnalysis bounded context (ADR-001, ADR-008 tactical depth).

Canonical: ``.pi/architecture/modules/consensus-analysis.md``

Everything in this context is derived. A consensus record, a compromise package, a scenario and an
impact assessment are projections over a closed run log; none of them is a source of truth. The
context therefore owns no negotiation state and is rebuildable at will (invariant 1).
"""

from __future__ import annotations

__all__: list[str] = []
