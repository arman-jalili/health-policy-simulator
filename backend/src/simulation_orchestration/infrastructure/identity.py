"""Deterministic identities for graph nodes.

The invocation id is reproducible and unique per run/round/actor/purpose. It is not a stance
derivation: model decisions come from the prompt or the persona policy, never from a hash.
"""

from __future__ import annotations

import hashlib

from simulation_orchestration.application.values import InvocationId


def invocation_identity(run_id: object, round_: int, actor: str, purpose: str) -> InvocationId:
    material = f"{run_id}|{round_}|{actor}|{purpose}".encode()
    return InvocationId("inv_" + hashlib.sha256(material).hexdigest()[:26])
