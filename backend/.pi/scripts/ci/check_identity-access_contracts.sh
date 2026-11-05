#!/usr/bin/env bash
# ============================================================================
# check_identity-access_contracts.sh — deterministic IdentityAccess proofing
#
# Verifies that the frozen contract has concrete implementations, that the DTOs
# and admin routes still exist, that migration 0104 owns the key table, and that
# the context is wired into the app shell. HTTP handlers are concrete: this
# checker only requires the router file, never a handler interface/impl pair.
#
# Usage: bash .pi/scripts/ci/check_identity-access_contracts.sh [--help]
# Exit:  0 = conformant, 1 = violation(s).
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

if [[ "${1:-}" == "--help" ]]; then
    sed -n '3,16p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
fi

SRC="src/identity_access"
PASS=0
FAIL=0

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✅${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}❌${NC} $1"; FAIL=$((FAIL + 1)); }

require_file() {
    local file="$1" desc="$2"
    if [[ -f "$file" ]]; then pass "$desc"; else fail "$desc — missing $file"; fi
}

require_literal() {
    local file="$1" needle="$2" desc="$3"
    if [[ ! -f "$file" ]]; then fail "$desc — missing $file"; return; fi
    if grep -Fq -- "$needle" "$file"; then
        pass "$desc"
    else
        fail "$desc — '$needle' not found in $file"
    fi
}

require_method() {
    local file="$1" method="$2" desc="$3"
    if [[ ! -f "$file" ]]; then fail "$desc — missing $file"; return; fi
    if grep -Eq "def[[:space:]]+${method}[[:space:]]*\(" "$file"; then
        pass "$desc"
    else
        fail "$desc — method ${method} missing in $file"
    fi
}

require_absent_recursive() {
    local path="$1" needle="$2" desc="$3"
    local hits
    hits=$(grep -Rn --include='*.py' -F -- "$needle" "$path" 2>/dev/null || true)
    if [[ -z "$hits" ]]; then pass "$desc"; else fail "$desc — found: $hits"; fi
}

echo "============================================"
echo "  IdentityAccess Contract Proofing"
echo "============================================"

echo ""
echo "--- Layer structure ---"
for layer in domain application infrastructure interfaces; do
    require_file "$SRC/$layer/__init__.py" "layer $layer/"
done

echo ""
echo "--- Ports and concrete implementations ---"
require_file "$SRC/interfaces/ports.py" "contract ports file"
for entry in \
    "PrincipalPort:resolve" \
    "ApiKeyAdminPort:create_key" \
    "ApiKeyAdminPort:list_keys" \
    "ApiKeyAdminPort:revoke_key" \
    "ReadinessPort:check" \
    "DemoModePolicy:permits"
do
    interface="${entry%%:*}"
    method="${entry##*:}"
    require_literal "$SRC/interfaces/ports.py" "class ${interface}(Protocol)" "port ${interface}"
    require_method "$SRC/interfaces/ports.py" "$method" "port method ${interface}.${method}"
done

require_method "$SRC/infrastructure/key_resolver.py" resolve "KeyResolver implements PrincipalPort.resolve"
require_method "$SRC/infrastructure/resolvers.py" resolve "StaticPrincipalResolver implements PrincipalPort.resolve"
for method in create_key list_keys revoke_key lookup; do
    require_method "$SRC/infrastructure/key_store.py" "$method" "HashedApiKeyStore.${method}"
done
for readiness in "readiness.py:DatabaseReadiness" "readiness.py:AlwaysReadyReadiness"; do
    file="${readiness%%:*}"; cls="${readiness##*:}"
    require_literal "$SRC/infrastructure/$file" "class ${cls}" "readiness adapter ${cls}"
    require_method "$SRC/infrastructure/$file" check "${cls}.check"
done
require_literal "$SRC/infrastructure/demo.py" "class LoopbackDemoPolicy" "demo policy adapter"
require_method "$SRC/infrastructure/demo.py" permits "LoopbackDemoPolicy.permits"
require_literal "$SRC/infrastructure/keys.py" "class Sha256ApiKeyFactory" "key factory"
require_method "$SRC/infrastructure/keys.py" generate "Sha256ApiKeyFactory.generate"

for repository in "repository/sqlalchemy.py:SqlAlchemyApiKeyRepository" "repository/memory.py:InMemoryApiKeyRepository" "repository/uow.py:UnitOfWorkApiKeyRepository"; do
    file="${repository%%:*}"; cls="${repository##*:}"
    require_literal "$SRC/infrastructure/$file" "class ${cls}" "repository adapter ${cls}"
    for method in add get find_by_hash list revoke; do
        require_method "$SRC/infrastructure/$file" "$method" "${cls}.${method}"
    done
done

echo ""
echo "--- Frozen DTOs ---"
require_file "$SRC/interfaces/dto.py" "DTO module"
for cls in CreateApiKeyCommand IssuedApiKey ApiKeySummary ResolutionOutcome ReadinessCheck ReadinessReport LivenessReport; do
    require_literal "$SRC/interfaces/dto.py" "class ${cls}" "DTO ${cls}"
done
require_literal "$SRC/interfaces/dto.py" "key: str = field(repr=False)" "plaintext key is repr-hidden"
require_literal "$SRC/interfaces/dto.py" "revoked_at: datetime | None" "summary tracks revocation"
require_file "$SRC/interfaces/http/schemas.py" "HTTP schema module"
for cls in CreateApiKeyRequest IssuedApiKeyResponse ApiKeySummaryResponse; do
    require_literal "$SRC/interfaces/http/schemas.py" "class ${cls}" "HTTP schema ${cls}"
done

echo ""
echo "--- API surface ---"
require_file "$SRC/interfaces/http/router.py" "concrete admin router (no handler interface)"
require_literal "$SRC/interfaces/http/router.py" '"/keys"' "POST/GET /api/v1/admin/keys"
require_literal "$SRC/interfaces/http/router.py" '"/keys/{key_id}"' "DELETE /api/v1/admin/keys/{key_id}"
require_literal "$SRC/interfaces/http/router.py" 'x-required-scope' "routes declare required scope"
require_literal "$SRC/interfaces/http/router.py" 'require_scope(Scope.ADMIN)' "admin scope enforced"
require_literal "$SRC/interfaces/http/router.py" 'get_api_key_admin' "store dependency"
require_literal "src/shared/http/health.py" '"/healthz"' "unauthenticated /healthz"
require_literal "src/shared/http/health.py" '"/readyz"' "unauthenticated /readyz"
require_literal "src/shared/http/health.py" '_check_llm' "readiness reports LLM reachability"

echo ""
echo "--- Persistence and wiring ---"
require_literal "$SRC/infrastructure/repository/models.py" 'identity_access_api_key' "ORM table identity_access_api_key"
require_file "migrations/versions/0104_identity_access.py" "migration 0104"
require_literal "migrations/versions/0104_identity_access.py" 'identity_access_api_key' "migration owns the key table"
require_literal "src/shared/app.py" 'build_identity_access_container' "composition root builds the container"
require_literal "src/shared/app.py" 'identity_access_router' "admin router mounted"
require_literal "src/shared/app.py" 'app.state.identity_access' "container exposed on app state"

echo ""
echo "--- Residue and ACL boundary ---"
require_absent_recursive "$SRC" "NotImplementedError" "no NotImplementedError residue"
require_absent_recursive "$SRC" "TODO(issue" "no stale issue TODOs"
if [[ -d "$SRC/interfaces" ]] && ! grep -Rq --include='*.py' 'identity_access.infrastructure' "$SRC/interfaces"; then
    pass "interfaces never import key-store infrastructure"
else
    fail "interfaces import key-store infrastructure"
fi

echo ""
echo "============================================"
echo "  Passed: ${PASS}  Failed: ${FAIL}"
echo "============================================"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
