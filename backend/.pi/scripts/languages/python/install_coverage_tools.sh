#!/usr/bin/env bash
# ============================================================================
# install_coverage_tools.sh — Python: install coverage.py (+ pytest)
#
# Installs the real coverage tooling used by
# .pi/scripts/languages/python/coverage.sh.
# ============================================================================
set -euo pipefail

if python3 -m coverage --version >/dev/null 2>&1; then
    echo "coverage.py already installed: $(python3 -m coverage --version | head -1)"
else
    echo "Installing coverage.py..."
    python3 -m pip install coverage
fi

if ! python3 -m pytest --version >/dev/null 2>&1; then
    echo "Installing pytest (optional, for test discovery)..."
    python3 -m pip install pytest || true
fi

echo "coverage tooling ready."
