#!/usr/bin/env bash
# Stage: deterministic proofing of the EvidenceCorpus contract.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -x ".venv/bin/python" && -z "${VIRTUAL_ENV:-}" ]]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
fi

python3 "${SCRIPT_DIR}/check_evidence_corpus_contract.py"
