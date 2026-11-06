#!/usr/bin/env bash
# Stage: deterministic proofing of the ConsensusAnalysis contract (epic #304, issue #322).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -x ".venv/bin/python" && -z "${VIRTUAL_ENV:-}" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

bash "${SCRIPT_DIR}/check_consensus-analysis_contracts.sh"
PYTHONPATH=src pytest tests/unit/consensus-analysis tests/integration/test_consensus_e2e.py \
    -m "not integration" -q
