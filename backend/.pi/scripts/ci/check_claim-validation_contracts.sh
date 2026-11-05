#!/usr/bin/env bash
# ============================================================================
# check_claim-validation_contracts.sh — deterministic ClaimValidation proofing
# Verifies the frozen contract is implemented, routed, persisted and mounted.
# Exit: 0 = conformant, 1 = violation(s).
# ============================================================================
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1
SRC="src/claim_validation"
PASS=0
FAIL=0
GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
pass() { echo -e "  ${GREEN}✅${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo -e "  ${RED}❌${NC} $1"; FAIL=$((FAIL + 1)); }
require_file() { [[ -f "$1" ]] && pass "$2" || fail "$2 — missing $1"; }
require_literal() {
    [[ -f "$1" ]] || { fail "$3 — missing $1"; return; }
    grep -Fq -- "$2" "$1" && pass "$3" || fail "$3 — '$2' not in $1"
}
require_method() {
    [[ -f "$1" ]] || { fail "$3 — missing $1"; return; }
    grep -Eq "def[[:space:]]+$2[[:space:]]*\\(" "$1" && pass "$3" || fail "$3 — method $2 missing"
}
require_absent() {
    local hits; hits=$(grep -Rn --include='*.py' -F -- "$2" "$1" 2>/dev/null || true)
    [[ -z "$hits" ]] && pass "$3" || fail "$3 — $hits"
}

echo "============================================"
echo "  ClaimValidation Contract Proofing"
echo "============================================"

echo ""; echo "--- Layers ---"
for layer in domain application infrastructure interfaces; do require_file "$SRC/$layer/__init__.py" "layer $layer/"; done

echo ""; echo "--- Domain ---"
for cls in ClaimType VerificationVerdict VerificationPath CausalSupport MeasureReference ToleranceBand ReferenceFigure VerificationEvidence; do
    require_literal "$SRC/domain/values.py" "class ${cls}" "value object ${cls}"
done
for cls in ClaimVerification ContradictionFinding ExpertReview; do require_literal "$SRC/domain/entities.py" "class ${cls}" "entity ${cls}"; done
require_literal "$SRC/domain/claim.py" "class Claim" "Claim aggregate"
for method in verify mark_unsupported escalate resolve_review drain_events; do
    require_method "$SRC/domain/claim.py" "$method" "Claim.${method}"
done
for cls in ResolveMeasureIdentity FigureComparison ContradictionDetector CausalAppraiser; do
    require_literal "$SRC/domain/services.py" "class ${cls}" "domain service ${cls}"
done
for event in ClaimExtracted ClaimVerified ClaimRejected UnsupportedAssertionFlagged ContradictionDetected ReferenceFigureRegistered ClaimEscalatedForReview ExpertReviewResolved ClaimMarkedUnverifiable CausalClaimAppraised; do
    require_literal "$SRC/domain/events.py" "class ${event}" "event ${event}"
done
for code in PATH_NOT_APPLICABLE REFERENCE_FIGURE_NOT_AUTHORITATIVE REVIEW_NOT_ESCALATED CLAIM_NOT_FOUND; do
    require_literal "$SRC/domain/errors.py" "$code" "error code ${code}"
done

echo ""; echo "--- Application ---"
for cls in VerifyClaim FlagUnsupportedAssertion GetClaim RegisterReferenceFigure ListReferenceFigures ListContradictions RecordContradiction ResolveExpertReview; do
    require_literal "$SRC/application/services.py" "class ${cls}" "service ${cls}"
done
for cls in VerifyClaimRequest FlagUnsupportedAssertionRequest GetClaimRequest RegisterReferenceFigureRequest ListReferenceFiguresRequest ListContradictionsRequest ResolveExpertReviewRequest; do
    require_literal "$SRC/application/commands.py" "class ${cls}" "request ${cls}"
done
for cls in ClaimVerdictResult ClaimDetailResult ReferenceFigureResult ContradictionResult; do
    require_literal "$SRC/application/dto.py" "class ${cls}" "result ${cls}"
done

echo ""; echo "--- API and ACL ---"
for path in '"/claims:verify"' '"/claims/{claim_id}:flag"' '"/claims/{claim_id}"' '"/reference-figures"' '"/contradictions"' '"/claims/{claim_id}/reviews"'; do
    require_literal "$SRC/interfaces/http/router.py" "$path" "route $path"
done
require_literal "$SRC/interfaces/http/router.py" 'x-required-scope' "routes declare scopes"
require_literal "$SRC/interfaces/published.py" "class ClaimVerdictView" "published verdict view"
if grep -Eq 'sqlalchemy|asyncpg|psycopg|infrastructure|Vector' "$SRC/interfaces/published.py"; then
    fail "published view leaks persistence/vectors"
else
    pass "published view has no persistence/vector imports"
fi

echo ""; echo "--- Persistence and wiring ---"
require_file "$SRC/composition.py" "composition root"
require_method "$SRC/composition.py" build_container "build_container"
require_literal "$SRC/composition.py" "SqlAlchemyClaimRepository" "Postgres claim repository wired"
require_literal "$SRC/composition.py" "Persistence.POSTGRES" "persistence switch present"
require_literal "src/shared/app.py" "claim_validation_router" "router mounted in app shell"
require_literal "src/shared/app.py" "app.state.claim_validation" "container exposed on app state"
require_file "migrations/versions/0301_claim_validation.py" "migration 0301"
for table in claim_validation_claim claim_validation_reference_figure claim_validation_contradiction; do
    require_literal "migrations/versions/0301_claim_validation.py" "$table" "table ${table}"
done
require_literal ".pi/architecture/decisions/ADR-012-claim-validation-runtime-integration.md" "**Status:** Accepted" "ADR-012 Accepted"
require_absent "$SRC" "NotImplementedError" "no NotImplementedError residue"

echo ""; echo "--- Capability proofs ---"
require_literal "$SRC/infrastructure/number_parser.py" "class GermanNumberParser" "German number parser"
require_literal "$SRC/application/services.py" "ResolveMeasureIdentity" "measure identity used at boundary"
require_literal "$SRC/application/services.py" "record_contradiction" "contradiction pipeline wired"
require_literal "$SRC/domain/services.py" "finding_for" "contradiction detector has a finding API"
require_literal "$SRC/infrastructure/number_parser.py" "len(matches) != 1" "ambiguous number refusal"
require_literal "tests/integration/test_claim_validation_wiring.py" "test_contradictions_are_produced_and_idempotent" "contradiction API proof"
require_literal "tests/integration/test_claim_validation_wiring.py" "test_measure_variants_normalise_at_the_api_boundary" "measure boundary proof"
for test in test_aggregate_root_claim.py test_type_dispatch.py test_tolerance.py test_real_contradiction.py test_reference_provenance.py test_german_number_parsing.py test_measure_identity.py; do
    found=$(find tests/unit/claim-validation -name "$test" | head -1)
    [[ -n "$found" ]] && pass "unit proof $test" || fail "unit proof $test missing"
done
require_file "tests/integration/test_claim_validation_wiring.py" "public-API wiring proof"
require_file "tests/integration/test_claim_validation_persistence.py" "restart persistence proof"

echo ""; echo "============================================"
echo "  Passed: ${PASS}  Failed: ${FAIL}"
echo "============================================"
[[ "$FAIL" -gt 0 ]] && exit 1
exit 0
