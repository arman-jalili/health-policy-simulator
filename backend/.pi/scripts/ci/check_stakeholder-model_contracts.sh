#!/usr/bin/env bash
# ============================================================================
# check_stakeholder-model_contracts.sh — deterministic StakeholderModel proofing
#
# Verifies that the frozen contract has concrete implementations, all eight
# routes and DTOs still exist, the nine personas are present and grounded, the
# allowlist is published, ADR-011 is Accepted, and the context is mounted in the
# app shell. HTTP handlers are concrete: only the router file is required.
#
# Usage: bash .pi/scripts/ci/check_stakeholder-model_contracts.sh [--help]
# Exit:  0 = conformant, 1 = violation(s).
# ============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

if [[ "${1:-}" == "--help" ]]; then
    sed -n '3,15p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
fi

SRC="src/stakeholder_model"
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
    if grep -Fq -- "$needle" "$file"; then pass "$desc"; else fail "$desc — '$needle' not found in $file"; fi
}

require_method() {
    local file="$1" method="$2" desc="$3"
    if [[ ! -f "$file" ]]; then fail "$desc — missing $file"; return; fi
    if grep -Eq "def[[:space:]]+${method}[[:space:]]*\\(" "$file"; then pass "$desc"; else fail "$desc — method ${method} missing in $file"; fi
}

require_absent_recursive() {
    local path="$1" needle="$2" desc="$3"
    local hits
    hits=$(grep -Rn --include='*.py' -F -- "$needle" "$path" 2>/dev/null || true)
    if [[ -z "$hits" ]]; then pass "$desc"; else fail "$desc — found: $hits"; fi
}

echo "============================================"
echo "  StakeholderModel Contract Proofing"
echo "============================================"

echo ""
echo "--- Layer structure ---"
for layer in domain application infrastructure interfaces; do
    require_file "$SRC/$layer/__init__.py" "layer $layer/"
done

echo ""
echo "--- Value objects and aggregates ---"
for cls in InstitutionIdentity Interest Constraint BudgetLimit DecisionPriority MandateScope MandateSource VetoRight Dependency NegotiatingPower AttributionStrength HistoricalPosition MaterialityScore; do
    require_literal "$SRC/domain/values.py" "class ${cls}" "value object ${cls}"
done
require_literal "$SRC/domain/stakeholder.py" "class Stakeholder" "Stakeholder aggregate"
require_literal "$SRC/domain/stakeholder.py" "class StakeholderProfile" "StakeholderProfile"
require_literal "$SRC/domain/agent_binding.py" "class AgentBinding" "AgentBinding aggregate"
require_literal "$SRC/domain/agent_binding.py" "@dataclass(frozen=True" "AgentBinding is frozen"
for method in cite_power_source record_historical_position negotiating_power activate; do
    require_method "$SRC/domain/stakeholder.py" "$method" "Stakeholder.${method}"
done

echo ""
echo "--- Errors and events ---"
for cls in PersonRepresentationForbidden IncompleteProfile UnsourcedAuthority VetoNarrowedToProposal BindingIncomplete StakeholderNotFound AgentBindingNotFound; do
    require_literal "$SRC/domain/errors.py" "class ${cls}" "error ${cls}"
done
for cls in StakeholderRegistered StakeholderProfileUpdated AgentPersonaBound HistoricalPositionRecorded MandateViolationDetected MandateSourceCited AuthorityClaimRejected WeakAttributionFlagged NegotiatingPowerChanged VetoRightRegistered DependencyRecorded; do
    require_literal "$SRC/domain/events.py" "class ${cls}" "event ${cls}"
done

echo ""
echo "--- Ports and implementations ---"
for entry in "StakeholderRepository:get" "StakeholderRepository:save" "StakeholderRepository:all_registered" "AgentBindingRepository:get_for_run" "AgentBindingRepository:save" "CorpusEvidencePort:passages_about"; do
    interface="${entry%%:*}"; method="${entry##*:}"
    require_literal "$SRC/domain/repositories.py" "class ${interface}(Protocol)" "port ${interface}"
    require_method "$SRC/domain/repositories.py" "$method" "port method ${interface}.${method}"
done
require_literal "$SRC/infrastructure/repository/memory.py" "class InMemoryStakeholderRepository" "memory stakeholder adapter"
require_literal "$SRC/infrastructure/repository/memory.py" "class InMemoryAgentBindingRepository" "memory binding adapter"
require_literal "$SRC/infrastructure/guard.py" "class InstitutionalAllowlistGuard" "allowlist guard adapter"
require_method "$SRC/infrastructure/guard.py" publish_allowlist "guard publishes allowlist"
require_method "$SRC/infrastructure/guard.py" recognises "guard recognises institution"

echo ""
echo "--- Domain services ---"
for entry in "TopicOverlapScorer:score" "WeightedInterestScorer:score" "ExplicitAttribution:classify" "ReportedAttribution:classify" "MentionOnly:classify"; do
    cls="${entry%%:*}"; method="${entry##*:}"
    require_literal "$SRC/domain/services.py" "class ${cls}" "domain service ${cls}"
    require_method "$SRC/domain/services.py" "$method" "${cls}.${method}"
done
require_method "$SRC/domain/services.py" select_current_position "weak-vs-explicit selection"
require_method "$SRC/domain/values.py" derive "NegotiatingPower derivation"
require_literal "$SRC/domain/services.py" "waiting_times" "German topic aliases present"

echo ""
echo "--- Application services and DTOs ---"
for cls in RegisterStakeholder UpdateStakeholderProfile CitePowerSource RecordHistoricalPosition SelectRelevantStakeholders BindAgentPersona GetStakeholderProfile ListStakeholders ListHistoricalPositions LoadPersonaCards PublishInstitutionalAllowlist; do
    require_literal "$SRC/application/services.py" "class ${cls}" "service ${cls}"
done
require_absent_recursive "$SRC/application" "NotImplementedError" "no application stubs remain"
for cls in RegisterStakeholderRequest UpdateStakeholderProfileRequest CitePowerSourceRequest RecordHistoricalPositionRequest ListHistoricalPositionsRequest SelectRelevantStakeholdersRequest BindAgentPersonaRequest GetStakeholderRequest ListStakeholdersRequest; do
    require_literal "$SRC/application/commands.py" "class ${cls}" "request ${cls}"
done
for cls in StakeholderSummaryResult StakeholderProfileResult RegisterStakeholderResult UpdateProfileResult CitePowerSourceResult HistoricalPositionResult HistoricalPositionsResult SelectionResult SelectStakeholdersResult BindingResult BindPersonasResult PersonaCardResult InstitutionalAllowlistResult; do
    require_literal "$SRC/application/dto.py" "class ${cls}" "result ${cls}"
done
for cls in UnitOfWork Clock InstitutionalGuardPort PersonaLoaderPort; do
    require_literal "$SRC/application/ports.py" "class ${cls}" "port ${cls}"
done

echo ""
echo "--- Partner contract ---"
for cls in StakeholderProfileView AgentBindingView InstitutionalAllowlistView; do
    require_literal "$SRC/interfaces/published.py" "class ${cls}" "published view ${cls}"
done
for fn in to_profile_view to_binding_view to_allowlist_view; do
    require_method "$SRC/interfaces/published.py" "$fn" "ACL mapper ${fn}"
done
if grep -Eq 'sqlalchemy|asyncpg|psycopg|infrastructure' "$SRC/interfaces/published.py"; then
    fail "partner contract imports persistence/infrastructure"
else
    pass "partner contract has no persistence imports"
fi

echo ""
echo "--- API surface ---"
require_file "$SRC/interfaces/http/router.py" "concrete router (no handler interface)"
for path in '"/stakeholders"' '"/stakeholders/{stakeholder_id}"' '"/stakeholders/{stakeholder_id}/powers"' '"/stakeholders/{stakeholder_id}/history"' '"/runs/{run_id}/stakeholders:select"' '"/runs/{run_id}/stakeholders:bind"'; do
    require_literal "$SRC/interfaces/http/router.py" "$path" "route $path"
done
require_literal "$SRC/interfaces/http/router.py" 'x-required-scope' "routes declare required scope"
require_file "$SRC/interfaces/http/mappers.py" "HTTP mappers"

echo ""
echo "--- Persona cards ---"
persona_count=$(find config/personas -maxdepth 1 -name '*.yaml' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$persona_count" == "9" ]]; then pass "nine persona cards present"; else fail "expected 9 persona cards, found ${persona_count}"; fi
for file in config/personas/*.yaml; do
    [[ -f "$file" ]] || continue
    if grep -q '^interests:' "$file" && grep -q '^constraints:' "$file"; then
        pass "persona $(basename "$file") has interests and constraints"
    else
        fail "persona $(basename "$file") lacks interests or constraints"
    fi
done

echo ""
echo "--- Wiring and ADR ---"
require_file "$SRC/composition.py" "composition root"
require_method "$SRC/composition.py" build_container "build_container"
require_literal "$SRC/composition.py" "PersonaFactory" "boot loads personas"
require_literal "$SRC/composition.py" "PublishInstitutionalAllowlist" "allowlist service wired"
require_literal "src/shared/app.py" "stakeholder_model_router" "router mounted in app shell"
require_literal "src/shared/app.py" "app.state.stakeholder_model" "container exposed on app state"
require_literal ".pi/architecture/decisions/ADR-011-stakeholder-model-runtime-integration.md" "**Status:** Accepted" "ADR-011 Accepted"
require_absent_recursive "$SRC" "NotImplementedError" "no NotImplementedError residue"

echo ""
echo "============================================"
echo "  Passed: ${PASS}  Failed: ${FAIL}"
echo "============================================"
if [[ "$FAIL" -gt 0 ]]; then exit 1; fi
exit 0
