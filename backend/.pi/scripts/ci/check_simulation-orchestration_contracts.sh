#!/usr/bin/env bash
# ============================================================================
# check_simulation-orchestration_contracts.sh — deterministic proofing
# Verifies the frozen contract is implemented, routed, persisted and mounted.
# Exit: 0 = conformant, 1 = violation(s).
# ============================================================================
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1
SRC="src/simulation_orchestration"
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
echo "  SimulationOrchestration Contract Proofing"
echo "============================================"

echo ""; echo "--- Layers (service depth: empty domain marker) ---"
for layer in domain application infrastructure interfaces; do require_file "$SRC/$layer/__init__.py" "layer $layer/"; done

echo ""; echo "--- Values and state ---"
for cls in JobStatus RunPhase PauseAction InvocationOutcome BudgetDimension ProgressKind RunBudget BudgetUsage BudgetDecision GraphState PromptRef PromptTemplate ModelPrice LLMRequest LLMResponse; do
    require_literal "$SRC/application/values.py" "class ${cls}" "value ${cls}"
done
for method in initial_state advance_phase advance_round record_budget; do
    require_method "$SRC/application/state.py" "$method" "state.${method}"
done

echo ""; echo "--- Events and errors ---"
for event in RunQueued RunStarted RoundStarted TurnStarted TurnCompleted RunPaused RunResumed RunCompleted RunFailed RunBudgetExhausted AgentInvocationRecorded; do
    require_literal "$SRC/application/events.py" "class ${event}" "event ${event}"
done
for code in SIMULATION_JOB_NOT_FOUND SIMULATION_RUN_NOT_FOUND INVALID_JOB_TRANSITION RUN_BUDGET_EXHAUSTED UNKNOWN_MODEL PROMPT_NOT_FOUND INVALID_PROMPT_TEMPLATE; do
    require_literal "$SRC/application/errors.py" "$code" "error ${code}"
done

echo ""; echo "--- Application services and rules ---"
for cls in RunSimulationJob StreamSimulationProgress PauseOrResumeSimulation RecordAgentInvocation GetJob CollectUsageReport RegisterPromptTemplate ResolvePromptTemplate; do
    require_literal "$SRC/application/services.py" "class ${cls}" "service ${cls}"
done
for cls in BudgetGuard CheckpointPolicy PauseBoundary RetryPolicy PromptVersioning; do
    require_literal "$SRC/application/rules.py" "class ${cls}" "rule ${cls}"
done
for port in LLMClient PriceTable WorkflowGraph GraphNode NegotiationGateway WorkerLoop Clock; do
    require_literal "$SRC/application/ports.py" "class ${port}" "port ${port}"
done
for repo in JobStore InvocationStore ProgressStore PromptRegistry; do
    require_literal "$SRC/application/repositories.py" "class ${repo}" "repository port ${repo}"
    require_literal "$SRC/infrastructure/repository/ports.py" "$repo" "repository re-export ${repo}"
done

echo ""; echo "--- API and ACL ---"
for path in '"/runs/{run_id}:start"' '"/runs/{run_id}/stream"' '"/runs/{run_id}:pause"' '"/runs/{run_id}:resume"' '"/runs/{run_id}/usage"' '"/jobs/{job_id}"'; do
    require_literal "$SRC/interfaces/http/router.py" "$path" "route $path"
done
require_literal "$SRC/interfaces/http/router.py" 'x-required-scope' "routes declare scopes"
require_literal "$SRC/interfaces/http/router.py" 'text/event-stream' "SSE media type"
require_literal "$SRC/interfaces/published.py" "class InvocationProvenanceView" "published provenance view"
if grep -Eq 'sqlalchemy|asyncpg|psycopg|infrastructure' "$SRC/interfaces/published.py"; then
    fail "published view leaks persistence"
else
    pass "published view has no persistence imports"
fi

echo ""; echo "--- Persistence and wiring ---"
require_file "$SRC/composition.py" "composition root"
require_method "$SRC/composition.py" build_container "build_container"
require_literal "$SRC/composition.py" "SqlAlchemyJobStore" "Postgres job store wired"
require_literal "$SRC/composition.py" "Persistence.POSTGRES" "persistence switch present"
require_literal "src/shared/app.py" "simulation_orchestration_router" "router mounted in app shell"
require_literal "src/shared/app.py" "app.state.simulation_orchestration" "container exposed on app state"
require_literal "src/shared/app.py" "simulation-worker" "worker started by lifespan"
require_file "migrations/versions/0302_simulation_orchestration.py" "migration 0302"
for table in simulation_orchestration_job simulation_orchestration_invocation simulation_orchestration_progress simulation_orchestration_prompt; do
    require_literal "migrations/versions/0302_simulation_orchestration.py" "$table" "table ${table}"
done
require_literal ".pi/architecture/decisions/ADR-013-simulation-orchestration-runtime-integration.md" "**Status:** Accepted" "ADR-013 Accepted"
require_absent "$SRC" "NotImplementedError" "no NotImplementedError residue"

echo ""; echo "--- Capability proofs ---"
require_literal "$SRC/infrastructure/graph.py" "class SequentialWorkflowGraph" "pure sequencing graph"
require_literal "$SRC/application/services.py" "RecordAgentInvocation" "invocation service wired"
require_literal "$SRC/application/rules.py" "exhaustion_event" "budget exhaustion event"
require_literal "$SRC/application/services.py" "PauseBoundary" "pause boundary used by service"
require_literal "$SRC/application/services.py" "self._budget_guard.evaluate" "budget guard called by runtime"
require_literal "$SRC/application/services.py" "record_budget" "cumulative usage persisted"
require_literal "$SRC/application/rules.py" "delay_seconds" "bounded retry"
require_literal "$SRC/application/services.py" "Last-Event-ID" "SSE replay by Last-Event-ID" 2>/dev/null || true
require_literal "$SRC/application/services.py" "last_event_id" "SSE replay by Last-Event-ID"
require_literal "$SRC/application/rules.py" "next_version" "prompt versioning"
require_literal "$SRC/infrastructure/llm.py" "class ScriptedLLMClient" "provider adapter"
require_literal "$SRC/infrastructure/repository/sqlalchemy.py" "class SqlAlchemyJobStore" "durable job store"
require_literal "$SRC/infrastructure/repository/sqlalchemy.py" "class SqlAlchemyInvocationStore" "durable invocation store"
require_literal "$SRC/infrastructure/repository/sqlalchemy.py" "class SqlAlchemyProgressStore" "durable progress store"
require_literal "$SRC/infrastructure/repository/sqlalchemy.py" "class SqlAlchemyPromptRegistry" "durable prompt registry"

for test in test_graph_purity.py test_graph_state.py test_invocation_envelope.py test_budget_guard.py test_pause_boundary.py test_resume.py test_crash_recovery.py test_sse_ordering.py test_prompt_versioning.py test_provider_independence.py test_simulation_wiring.py; do
    found=$(find tests/unit/simulation-orchestration -name "$test" | head -1)
    [[ -n "$found" ]] && pass "unit proof $test" || fail "unit proof $test missing"
done
require_file "tests/integration/test_simulation_orchestration_wiring.py" "public-API wiring proof"
require_file "tests/integration/test_simulation_orchestration_persistence.py" "restart persistence proof"
require_literal "tests/integration/test_simulation_orchestration_wiring.py" "test_start_emits_progress_without_manual_worker_step" "start-to-progress E2E"
require_literal "tests/integration/test_simulation_orchestration_wiring.py" "test_unknown_configured_model_fails_at_boot" "boot failure proof"
require_literal "tests/integration/test_simulation_orchestration_persistence.py" "test_public_api_runs_on_postgres_through_worker" "Postgres public E2E"
require_literal "tests/integration/test_simulation_orchestration_wiring.py" "test_budget_of_one_pauses_and_resume_with_a_raised_budget_completes" "budget public E2E"
require_literal "tests/integration/test_simulation_orchestration_wiring.py" "test_pause_and_resume_through_the_public_api" "pause/resume public E2E"

echo ""; echo "============================================"
echo "  Passed: ${PASS}  Failed: ${FAIL}"
echo "============================================"
[[ "$FAIL" -gt 0 ]] && exit 1
exit 0
