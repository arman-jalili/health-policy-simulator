#!/usr/bin/env bash
# Stage: full demo walkthrough against a migrated database (issues #412/#414).
set -uo pipefail
if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "  SKIP: DATABASE_URL is not set"
    exit 0
fi
if make demo-walkthrough; then
    echo "  ✓ PASS: demo walkthrough published a brief without manual provenance"
    exit 0
fi
echo "  ✗ FAIL: demo walkthrough"
exit 1
