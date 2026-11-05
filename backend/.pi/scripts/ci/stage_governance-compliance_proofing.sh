#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT"
if [[ -x ".venv/bin/python" && -z "${VIRTUAL_ENV:-}" ]]; then source ".venv/bin/activate"; fi
bash "${SCRIPT_DIR}/check_governance-compliance_contracts.sh"
PYTHONPATH=src pytest -m "not integration" -q --cov=src --cov-fail-under=80
