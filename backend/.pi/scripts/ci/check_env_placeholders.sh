#!/usr/bin/env bash
# Readiness env rule: only secret-shaped variables must differ from .env.example, and a
# secret-shaped value must never remain a documented placeholder.
#
# Usage: check_env_placeholders.sh [env-file] [example-file]
# Exit: 0 = rule satisfied (or files absent), 1 = a named variable violates the rule.
set -uo pipefail

ENV_FILE="${1:-.env}"
EXAMPLE_FILE="${2:-.env.example}"

[[ -f "$ENV_FILE" && -f "$EXAMPLE_FILE" ]] || exit 0

SECRET_SHAPE='(SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE_KEY|API_KEY|ACCESS_KEY|SECRET_KEY|CREDENTIAL|DSN)'
PLACEHOLDER='^(change[-_]?me|changeme|example|example[-_].*|replace[-_]?me|your[-_].*|secret|test|xxx+|todo|placeholder)$'

value_for() {
    local file="$1" name="$2"
    grep -E "^[[:space:]]*(export[[:space:]]+)?${name}=" "$file" 2>/dev/null \
        | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

failures=0
while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    value="$(value_for "$ENV_FILE" "$name")"
    [[ -n "$value" ]] || continue
    if [[ "$value" =~ $PLACEHOLDER ]]; then
        echo "$name: secret-shaped value is still a placeholder"
        ((failures++))
        continue
    fi
    if grep -Eq "^[[:space:]]*(export[[:space:]]+)?${name}=" "$EXAMPLE_FILE" 2>/dev/null; then
        example_value="$(value_for "$EXAMPLE_FILE" "$name")"
        if [[ "$value" == "$example_value" ]]; then
            echo "$name: secret-shaped value still equals .env.example"
            ((failures++))
        fi
    fi
done < <(
    grep -v '^[[:space:]]*#' "$ENV_FILE" 2>/dev/null \
        | sed -E 's/^[[:space:]]*(export[[:space:]]+)?//' \
        | cut -d= -f1 \
        | grep -E "$SECRET_SHAPE" \
        || true
)

if [[ $failures -gt 0 ]]; then
    echo "Exempt: DATABASE_URL and other non-secret-shaped variables may equal .env.example."
    exit 1
fi
echo "Secret-shaped variables are rotated and non-secret defaults may match .env.example."
exit 0
