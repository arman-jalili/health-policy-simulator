#!/usr/bin/env bash
# Deterministic proofing for the consensus-analysis contract (epic #304, issue #322).
#
# Zero-token gate: every check is a file, a literal or a count. It fails when an implemented
# contract member is removed, renamed or left as a stub, so the module cannot regress silently.
set -uo pipefail
PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); }
fail() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }
require_file() { [[ -f "$1" ]] && pass || fail "missing file $1"; }
require_literal() { grep -qF "$2" "$1" 2>/dev/null && pass || fail "$3 ($2 in $1)"; }
require_absent() { grep -qF "$2" "$1" 2>/dev/null && fail "$3 ($2 still in $1)" || pass; }

SRC="src/consensus_analysis"

# ── Layer structure ─────────────────────────────────────────────────────────────────────────────
for f in \
  "__init__.py" "composition.py" \
  "domain/values.py" "domain/entities.py" "domain/consensus_record.py" \
  "domain/compromise_package.py" "domain/scenario.py" "domain/services.py" \
  "domain/events.py" "domain/errors.py" "domain/repositories.py" \
  "application/commands.py" "application/dto.py" "application/ports.py" \
  "application/services.py" "application/estimators.py" \
  "infrastructure/acl.py" "infrastructure/projection.py" "infrastructure/comparison.py" \
  "infrastructure/sources.py" "infrastructure/repository/memory.py" \
  "infrastructure/repository/ports.py" \
  "interfaces/http/router.py" "interfaces/http/schemas.py" "interfaces/http/deps.py" \
  "interfaces/published.py"; do
  require_file "$SRC/$f"
done

# ── Vocabulary is closed ───────────────────────────────────────────────────────────────────────
for value in consensus partial veto_blocked unresolved; do
  require_literal "$SRC/domain/values.py" "$value" "outcome kind $value"
done
for value in measured derived modelled assumed not_estimated; do
  require_literal "$SRC/domain/values.py" "$value" "basis kind $value"
done
for value in evidenced modelled assumed; do
  require_literal "$SRC/domain/values.py" "$value" "uncertainty label $value"
done
for value in statutory_benefit_change budget_frame service_catalogue fee_schedule hospital_plan; do
  require_literal "$SRC/domain/values.py" "$value" "proposal class $value"
done

# ── Every component has a named home ──────────────────────────────────────────────────────────
for pair in "consensus_record.py:ConsensusRecord" "compromise_package.py:CompromisePackage" \
            "scenario.py:Scenario"; do
  require_literal "$SRC/domain/${pair%%:*}" "class ${pair##*:}" "aggregate ${pair##*:}"
done
for name in MajorityPosition MinorityPosition ImpactAssessment PackageComponent RejectedProposal; do
  require_literal "$SRC/domain/entities.py" "class $name" "entity $name"
done
for name in ConsensusRule NotVetoed ThresholdMet MajorityHolds MinorityCapture ComponentsCompatible \
            EstimateValidator IllustrativeValueGuard FeasibilityGuard; do
  require_literal "$SRC/domain/services.py" "class $name" "domain service $name"
done
for name in DeriveConsensus GetConsensus ListUnresolvedConflicts ComposeCompromisePackage ListPackages \
            AssessImpact CompareScenarios RebuildProjections HandleRunClosed; do
  require_literal "$SRC/application/services.py" "class $name" "use case $name"
done

# ── The eleven invariants have error codes ────────────────────────────────────────────────────
for code in STANCE_NOT_IN_HISTORY UNBACKED_ESTIMATE MISLABELED_ESTIMATE ILLUSTRATIVE_VALUE_REFUSED \
            FEASIBILITY_CONTRADICTS_VETO INCOMPATIBLE_COMPONENT INCOMPLETE_REJECTION_LIST \
            PACKAGE_STATE_TRANSITION INCOMPLETE_COMPARISON PROJECTION_REBUILD_FAILED \
            CONSENSUS_ANALYSIS_UNAVAILABLE; do
  require_literal "$SRC/domain/errors.py" "$code" "error code $code"
done

# ── All nine events exist ─────────────────────────────────────────────────────────────────────
for event in ConsensusDetermined ConsensusBlockedByVeto MinorityPositionRecorded \
             UnresolvedConflictDeclared CompromisePackageComposed ScenarioDefined ImpactAssessed \
             UnbackedEstimateBlocked FeasibilityRated; do
  require_literal "$SRC/domain/events.py" "class $event" "event $event"
done

# ── Ports ─────────────────────────────────────────────────────────────────────────────────────
for port in ConsensusRepository CompromisePackageRepository ScenarioRepository RunLogPort StakeholderPowersPort; do
  require_literal "$SRC/domain/repositories.py" "class $port" "repository port $port"
done
for port in Clock UnitOfWork IdFactory EventPublisher MandateThresholdSource ProjectionRebuilder \
            ComparisonRanker ComponentCatalogue IllustrativeValueSource LlmImpactEstimator; do
  require_literal "$SRC/application/ports.py" "class $port" "application port $port"
done

# ── The frozen API surface and its scopes ─────────────────────────────────────────────────────
for path in '/runs/{run_id}/analysis:derive' '/runs/{run_id}/consensus' '/runs/{run_id}/conflicts/open' \
            '/runs/{run_id}/packages' '/packages/{package_id}/scenarios' '/packages/{package_id}/comparison'; do
  require_literal "$SRC/interfaces/http/router.py" "$path" "route $path"
done
for scope in 'runs:write' 'runs:read'; do
  require_literal "$SRC/interfaces/http/router.py" "$scope" "scope $scope"
done

# ── Wiring obligations ────────────────────────────────────────────────────────────────────────
require_literal "src/shared/app.py" "build_consensus_container" "runtime composition"
require_literal "src/shared/app.py" "consensus_analysis_router" "runtime router"
require_literal "$SRC/infrastructure/sources.py" "class UnavailableRunLog" "run log fails closed"
require_literal "$SRC/infrastructure/sources.py" "class UnavailableMandate" "mandate fails closed"
require_literal "$SRC/infrastructure/sources.py" "class UnavailablePowers" "vetoes fail closed"
require_literal "$SRC/application/services.py" "SERVICE_CLASSIFICATION" "service classification"
require_literal ".pi/architecture/decisions/ADR-016-consensus-analysis-runtime-integration.md" \
  "**Status:** Accepted" "runtime ADR accepted"
require_file "docs/runbook-consensus-analysis.md"
require_file "docs/dr-plan-consensus-analysis.md"
require_literal "docs/runbook-consensus-analysis.md" "CONSENSUS_ANALYSIS_UNAVAILABLE" "runbook refusal"
require_literal "docs/dr-plan-consensus-analysis.md" "RTO" "DR recovery objective"
require_literal "src/shared/http/health.py" "consensus_analysis" "readiness check"

# ── Proofs exist ─────────────────────────────────────────────────────────────────────────────
require_file "tests/integration/test_consensus_e2e.py"
for proof in test_closing_a_run_produces_consensus_rows_with_no_api_call \
             test_rebuilding_twice_yields_byte_identical_records \
             test_seven_of_nine_support_for_a_vetoed_class_is_blocked_never_consensus \
             test_an_unbacked_estimate_is_refused_and_blocked_in_the_audit_trail \
             test_the_persistence_path_refuses_an_illustrative_value_before_writing; do
  grep -rqF "def $proof" tests/ && pass || fail "missing proof $proof"
done

# ── No stub may remain on an implemented path ────────────────────────────────────────────────
# The three estimation strategies are the only admitted stubs: their arithmetic is a calculation
# issue, and inventing a formula here is the defect the unbacked-estimate guard prevents.
expected_stubs=3
actual_stubs=$(grep -rc 'raise NotImplementedError' "$SRC" --include='*.py' | awk -F: '{s+=$2} END {print s}')
[[ "$actual_stubs" -eq "$expected_stubs" ]] && pass || fail "expected $expected_stubs stubs, found $actual_stubs"
for member in "CompromisePackage.open" "ConsensusRecord.digest" "EstimateValidator.validate"; do
  grep -rqF "raise NotImplementedError(\"$member" "$SRC" && fail "$member is still a stub" || pass
done

echo "============================================"
echo "  Passed: $PASS  Failed: $FAIL"
echo "============================================"
[[ $FAIL -eq 0 ]]
