#!/usr/bin/env bash
# Stage: deterministic proofing of the NegotiationSession contract + real coverage gate.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT"
if [[ -x ".venv/bin/python" && -z "${VIRTUAL_ENV:-}" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi
bash "${SCRIPT_DIR}/check_negotiation-session_contracts.sh"
PYTHONPATH=src pytest -m "not integration" -q --cov=src --cov-fail-under=80
