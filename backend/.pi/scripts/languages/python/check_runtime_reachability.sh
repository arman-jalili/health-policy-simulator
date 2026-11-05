#!/usr/bin/env bash
# ============================================================================
# check_runtime_reachability.sh — Python (ADR-009)
#
# Every module under src/<module>/application/ must be referenced from
# production code OUTSIDE its own module and OUTSIDE tests. Candidates: the
# file stem, its PascalCase class name, and the separator-stripped form
# (case-insensitive).
# Usage: bash check_runtime_reachability.sh [--root <dir>]
# Exit:  0 all reachable ; 1 dead service(s)
# ============================================================================
set -uo pipefail
ROOT="$(pwd)"
if [ "${1:-}" = "--root" ] && [ -n "${2:-}" ]; then ROOT="$2"; fi
cd "$ROOT" || exit 1
VIOLATIONS=0
[ -d src ] || { echo "runtime-reachability (python): no src/"; exit 0; }

while IFS= read -r svc; do
    [ -n "$svc" ] || continue
    mod="$(echo "$svc" | sed 's|^src/||; s|/application/.*||')"
    stem="$(basename "$svc" .py)"
    pascal="$(echo "$stem" | python3 -c 'import sys; s=sys.stdin.read().strip(); print("".join(w.capitalize() for w in s.replace("-","_").split("_")))' 2>/dev/null || echo "$stem")"
    compact="$(echo "$stem" | tr -d '_-')"
    refs="$(grep -rliE "\b(${pascal}|${stem}|${compact})\b" src 2>/dev/null | grep -vE "/tests?/|test_.*\.py$|_test\.py$|/test/" | grep -v "^src/${mod}/application/" | grep -v "^${svc}$" | grep -cv '^$' || true)"
    if [ "${refs:-0}" -eq 0 ]; then
        echo "$svc: [runtime-reachability] application service has no production caller outside its module (tests-only callers don't count — ADR-009)"
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
done < <(find src -path "*/application/*.py" -type f 2>/dev/null | grep -vE "/tests?/|test_.*\.py$|_test\.py$" || true)

if [ "$VIOLATIONS" -gt 0 ]; then echo "runtime-wiring (python): ${VIOLATIONS} unwired service(s)" >&2; exit 1; fi
echo "runtime-reachability (python): all application services reachable from production code"
exit 0
