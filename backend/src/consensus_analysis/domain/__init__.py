"""Domain layer of ConsensusAnalysis: aggregates, owned entities, value objects and rules.

ADR-008 justifies tactical depth here: thresholds, veto precedence and estimation provenance are
invariants (never workflow), so they need aggregates with identity and guards rather than a flat
rule chain. This layer carries no outer-layer dependency.
"""

from __future__ import annotations

__all__: list[str] = []
