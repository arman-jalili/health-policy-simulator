#!/usr/bin/env bash
# ============================================================================
# coverage.sh — Python: real line coverage via coverage.py
#
# Runs the test suite under coverage.py and reports the TOTAL line coverage.
# Uses pytest when available, unittest otherwise.
#
# Usage (normally via the .pi/scripts/coverage.sh dispatcher):
#   bash coverage.sh            # measure coverage
#   bash coverage.sh --gate     # fail if lines < COVERAGE_THRESHOLD
#   bash coverage.sh --lcov     # also write coverage.xml (cobertura) artifact
#
# Env:
#   COVERAGE_THRESHOLD  minimum line-coverage % (default: 60)
# ============================================================================
set -uo pipefail

COVERAGE_THRESHOLD="${COVERAGE_THRESHOLD:-60}"
GATE=0
LCOV=0

for arg in "$@"; do
    case "$arg" in
        --gate) GATE=1 ;;
        --lcov) LCOV=1 ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

# Walk up from CWD to the project root (pyproject.toml / setup.py /
# setup.cfg / requirements.txt).
ROOT="$(pwd)"
while [ "$ROOT" != "/" ] \
    && [ ! -f "$ROOT/pyproject.toml" ] \
    && [ ! -f "$ROOT/setup.py" ] \
    && [ ! -f "$ROOT/setup.cfg" ] \
    && [ ! -f "$ROOT/requirements.txt" ]; do
    ROOT="$(dirname "$ROOT")"
done
if [ ! -f "$ROOT/pyproject.toml" ] && [ ! -f "$ROOT/setup.py" ] \
    && [ ! -f "$ROOT/setup.cfg" ] && [ ! -f "$ROOT/requirements.txt" ]; then
    echo "✗ No Python project marker found in this directory tree" >&2
    exit 1
fi
cd "$ROOT" || exit 1

if ! python3 -m coverage --version >/dev/null 2>&1; then
    echo "coverage.py not found — run .pi/scripts/install_coverage_tools.sh" >&2
    exit 1
fi

echo "═══ Coverage (coverage.py) ═══"
# Scope measurement to the project source (src/ layout when present, else
# the project root) so site-packages / pytest internals are not counted.
COV_SOURCE="src"
[ -d "src" ] || COV_SOURCE="."
if python3 -m pytest --version >/dev/null 2>&1; then
    python3 -m coverage run --source="$COV_SOURCE" -m pytest -q >/dev/null 2>&1 || true
else
    python3 -m coverage run --source="$COV_SOURCE" -m unittest discover -s tests >/dev/null 2>&1 || true
fi

REPORT="$(python3 -m coverage report 2>&1 || true)"
echo "$REPORT" | tail -20
COVERAGE="$(echo "$REPORT" | awk '/^TOTAL/{print $NF}' | tr -d '%')"
echo ""
echo "Line coverage: ${COVERAGE:-unavailable}% (threshold: ${COVERAGE_THRESHOLD}%)"

if [ -z "$COVERAGE" ]; then
    echo "✗ Could not extract TOTAL coverage from coverage.py output" >&2
    exit 1
fi

if [ "$LCOV" -eq 1 ]; then
    python3 -m coverage xml -o coverage.xml >/dev/null 2>&1 \
        && echo "cobertura artifact written: coverage.xml" \
        || echo "⚠️  could not write coverage.xml" >&2
fi

if [ "$GATE" -eq 1 ]; then
    if awk "BEGIN { exit !($COVERAGE >= $COVERAGE_THRESHOLD) }"; then
        echo "✓ Coverage gate passed"
    else
        echo "✗ Coverage below threshold (${COVERAGE}% < ${COVERAGE_THRESHOLD}%)" >&2
        exit 1
    fi
fi
exit 0
