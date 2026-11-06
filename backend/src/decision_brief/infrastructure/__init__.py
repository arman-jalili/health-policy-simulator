"""Infrastructure layer of DecisionBrief (contract frozen, issue #331).

Adapters live here: the projection builder, the citation resolver, the provenance gate and the
repositories. Nothing in this layer may be imported by ``domain/``.
"""

from __future__ import annotations
