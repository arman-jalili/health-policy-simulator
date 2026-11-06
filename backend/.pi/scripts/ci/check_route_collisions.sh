#!/usr/bin/env bash
# Fail when two context routers register the same METHOD+path; OpenAPI silently keeps the last one.
set -euo pipefail
PYTHONPATH=src .venv/bin/python - <<'PY'
from collections import defaultdict
from evidence_corpus.interfaces.http.router import router as corpus
from evidence_retrieval.interfaces.http.router import router as retrieval
from identity_access.interfaces.http.router import router as identity
from stakeholder_model.interfaces.http.router import router as stakeholders
from claim_validation.interfaces.http.router import router as claims
from simulation_orchestration.interfaces.http.router import router as simulation
from governance_compliance.interfaces.http.router import router as governance
from consensus_analysis.interfaces.http.router import router as consensus
from negotiation_session.interfaces.http.router import router as negotiation
from decision_brief.interfaces.http.router import router as briefs

seen: dict[tuple[str, str], list[str]] = defaultdict(list)
for name, router in {
    "evidence_corpus": corpus,
    "evidence_retrieval": retrieval,
    "identity_access": identity,
    "stakeholder_model": stakeholders,
    "claim_validation": claims,
    "simulation_orchestration": simulation,
    "governance_compliance": governance,
    "consensus_analysis": consensus,
    "negotiation_session": negotiation,
    "decision_brief": briefs,
}.items():
    for route in router.routes:
        path = getattr(route, "path", None)
        if path is None:
            continue
        for method in getattr(route, "methods", set()):
            seen[(method, path)].append(name)

collisions = {key: owners for key, owners in seen.items() if len(owners) > 1}
if collisions:
    for (method, path), owners in sorted(collisions.items()):
        print(f"  ✗ {method} {path}: {', '.join(owners)}")
    raise SystemExit(1)
print(f"  ✓ PASS: no duplicate METHOD+path across {len(seen)} routes")
PY
