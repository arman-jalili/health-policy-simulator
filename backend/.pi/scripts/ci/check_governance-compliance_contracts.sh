#!/usr/bin/env bash
# Deterministic proofing for the governance-compliance contract.
set -uo pipefail
PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); }
fail() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }
require_file() { [[ -f "$1" ]] && pass || fail "missing file $1"; }
require_literal() { grep -qF "$2" "$1" 2>/dev/null && pass || fail "$3 ($2 in $1)"; }
SRC="src/governance_compliance"
for f in application/values.py application/commands.py application/dto.py application/ports.py application/repositories.py application/rules.py application/services.py application/errors.py application/events.py composition.py interfaces/http/router.py interfaces/http/schemas.py interfaces/published.py infrastructure/ner.py infrastructure/resolver.py infrastructure/repository/memory.py infrastructure/repository/sqlalchemy.py infrastructure/repository/models.py infrastructure/allowlist.py; do require_file "$SRC/$f"; done
require_file "src/governance_compliance/domain/__init__.py"
[[ $(find "$SRC/domain" -name '*.py' ! -name '__init__.py' | wc -l) -eq 0 ]] && pass || fail "domain has implementation modules"
for value in 'accept' 'rewrite' 'reject' 'person_named' 'personal_quotation' 'unsupported_fact' 'contradicted_figure' 'institution_ambiguous' 'GC-001' 'GC-002' 'GC-003' 'GC-004' 'GC-005'; do require_literal "$SRC/application/values.py" "$value" "value $value"; done
for name in EnforceInstitutionOnlyOutput DisclosePositionProvenance RecordGovernanceViolation ValidateInstitutionalAllowlist ListViolations GetPositionProvenance ListAllowlist; do require_literal "$SRC/application/services.py" "class $name" "service $name"; done
for rule in PersonReferenceRule PersonalQuotationRule InstitutionAliasRule UnsupportedFactRule ContradictedFigureRule GuardRuleChain; do require_literal "$SRC/application/rules.py" "class $rule" "rule $rule"; done
for path in '/governance/check' '/governance/violations' '/positions/{position_id}/provenance' '/governance/allowlist'; do require_literal "$SRC/interfaces/http/router.py" "$path" "route $path"; done
for scope in 'runs:write' 'runs:read' 'admin'; do require_literal "$SRC/interfaces/http/router.py" "$scope" "scope $scope"; done
for code in GOVERNANCE_VIOLATION_NOT_FOUND PROVENANCE_INCOMPLETE ALLOWLIST_EMPTY ALLOWLIST_CONTAINS_PERSON GUARD_VERDICT_REQUIRED GOVERNANCE_GUARD_UNAVAILABLE UNKNOWN_GOVERNANCE_RULE; do require_literal "$SRC/application/errors.py" "$code" "error $code"; done
require_literal "$SRC/application/events.py" "GovernanceViolationRecorded" "audit event"
require_literal "$SRC/interfaces/published.py" "GuardVerdictView" "guard published view"
require_literal "$SRC/interfaces/published.py" "PositionProvenanceView" "provenance published view"
require_literal "$SRC/composition.py" "def build_container" "composition factory"
require_literal "$SRC/composition.py" "governance_compliance_wired" "boot log"
require_literal "$SRC/infrastructure/allowlist.py" "from_published" "allowlist adapter"
require_literal "$SRC/infrastructure/repository/sqlalchemy.py" "SqlAlchemyViolationStore" "SQL violation store"
require_literal "$SRC/infrastructure/repository/sqlalchemy.py" "SqlAlchemyProvenanceStore" "SQL provenance store"
require_literal "src/shared/app.py" "build_governance_container" "runtime composition"
require_literal "src/shared/app.py" "governance_compliance_router" "runtime router"
require_literal "migrations/versions/0305_governance_compliance.py" "governance_compliance_violation" "violation table"
require_literal "migrations/versions/0305_governance_compliance.py" "governance_compliance_provenance" "provenance table"
require_literal ".pi/architecture/decisions/ADR-014-governance-compliance-runtime-integration.md" "**Status:** Accepted" "runtime ADR accepted"
require_literal "tests/integration/test_governance_e2e.py" "test_guard_rewrites_a_person_through_the_public_api" "public E2E proof"
require_literal "tests/integration/test_governance_persistence.py" "test_duplicate_retry_writes_exactly_one_violation" "persistence proof"
require_literal "tests/unit/governance-compliance/adversarial-suite/test_adversarial_suite.py" "PERSON_STRINGS" "adversarial corpus"
! grep -R "NotImplementedError" -n "$SRC" >/dev/null 2>&1 && pass || fail "NotImplementedError remains in src"
echo "============================================"
echo "  Passed: $PASS  Failed: $FAIL"
echo "============================================"
[[ $FAIL -eq 0 ]]
