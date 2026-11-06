#!/usr/bin/env bash
# Stage 18: DecisionBrief contract proofing + real coverage gate (epic #330, issue #347).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT"
if [[ -x ".venv/bin/python" && -z "${VIRTUAL_ENV:-}" ]]; then source ".venv/bin/activate"; fi
bash "${SCRIPT_DIR}/check_decision-brief_contracts.sh"
PYTHONPATH=src pytest tests/unit/decision-brief -m "not integration" -q \
  --cov=src/decision_brief --cov-fail-under=80
