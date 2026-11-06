"""Infrastructure layer of ConsensusAnalysis: ACL adapters and projection persistence.

Nothing here decides anything: adapters translate a published partner shape into a local value, and
the repositories write projections that a replay must be able to reproduce.
"""

from __future__ import annotations

__all__: list[str] = []
