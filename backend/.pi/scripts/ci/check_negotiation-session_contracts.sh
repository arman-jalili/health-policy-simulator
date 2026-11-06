#!/usr/bin/env bash
# ============================================================================
# check_negotiation-session_contracts.sh — deterministic NegotiationSession proofing
# Verifies the frozen contract is implemented, routed, wired and pure.
# Exit: 0 = conformant, 1 = violation(s).
# ============================================================================
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$PROJECT_ROOT" || exit 1
SRC="src/negotiation_session"
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
echo "  NegotiationSession Contract Proofing"
echo "============================================"

echo ""; echo "--- Layers ---"
for layer in domain application infrastructure interfaces; do require_file "$SRC/$layer/__init__.py" "layer $layer/"; done

echo ""; echo "--- Domain vocabulary ---"
for cls in NegotiationPhase ArgumentStance Proposal ProposalComponent RevisionReason StoppingCondition TurnAssignment ConsensusLevel LearningApplication ClaimEvidence; do
    require_literal "$SRC/domain/values.py" "class ${cls}" "value object ${cls}"
done
for cls in NegotiationMandate NegotiationRound Position Argument ConflictTopic Coalition CoalitionOffer RoundLearning; do
    require_literal "$SRC/domain/entities.py" "class ${cls}" "entity ${cls}"
done
require_literal "$SRC/domain/simulation_run.py" "class SimulationRun" "SimulationRun aggregate"
for method in open open_round submit_initial_position take_turn revise_position record_abstention track_conflict form_coalition close_round evaluate_stopping advance_phase drain_events; do
    require_method "$SRC/domain/simulation_run.py" "$method" "SimulationRun.${method}"
done
for cls in EvaluateStoppingCondition DetectArgumentContradiction RoundRobinTurnOrder PowerWeightedTurnOrder AffectedFirstTurnOrder; do
    require_literal "$SRC/domain/services.py" "class ${cls}" "domain service ${cls}"
done

echo ""; echo "--- Events and errors ---"
for event in SimulationRunOpened RoundOpened InitialPositionStated ArgumentSubmitted PositionRevised PositionRevisionRejected ConflictTopicOpened CoalitionOffered CoalitionOfferDeclined CoalitionFormed AbstentionRecorded RoundClosed RoundLearningCaptured LearningApplied NegotiationPhaseAdvanced SimulationRunClosed; do
    require_literal "$SRC/domain/events.py" "class ${event}" "event ${event}"
done
require_literal "$SRC/domain/events.py" "class LoggedEvent" "run-log record"
for code in PHASE_REGRESSION CLOSED_RUN_IMMUTABLE ROUND_CLOSE_GUARD_VIOLATION ROUND_LEARNING_MISSING REVISION_WITHOUT_CAUSE ARGUMENT_WITHOUT_EVIDENCE TURN_NOT_AVAILABLE DUPLICATE_TURN ROUND_CAP_EXCEEDED COALITION_WITHOUT_OFFER GOVERNANCE_GUARD_UNAVAILABLE; do
    require_literal "$SRC/domain/errors.py" "$code" "error code ${code}"
done

echo ""; echo "--- Application ---"
for cls in TranslateQuestionToMandate SelectRelevantStakeholders OpenSimulationRun SubmitInitialPosition TakeNegotiationTurn RevisePosition RecordAbstention TrackConflictTopic FormCoalition CloseRound GetSimulationRun ListRounds ListConflictTopics ListRoundLearning SummariseIntermediateResult ReplaySimulationHistory; do
    require_literal "$SRC/application/services.py" "class ${cls}" "service ${cls}"
done
require_literal "$SRC/application/services.py" "SERVICE_CLASSIFICATION" "service classification map"
for file in commands.py dto.py ports.py progress.py mappers.py; do require_file "$SRC/application/$file" "application/$file"; done

echo ""; echo "--- API and ACL ---"
for path in '"/runs"' '"/runs/{run_id}"' '"/runs/{run_id}/events"' '"/runs/{run_id}/rounds"' '"/runs/{run_id}/positions"' '"/runs/{run_id}/turns"' '"/runs/{run_id}/positions/{position_id}:revise"' '"/runs/{run_id}/abstentions"' '"/runs/{run_id}/conflicts"' '"/runs/{run_id}/coalitions"' '"/runs/{run_id}/learning"' '"/runs/{run_id}/negotiation/stream"'; do
    require_literal "$SRC/interfaces/http/router.py" "$path" "route $path"
done
require_literal "$SRC/interfaces/http/router.py" 'x-required-scope' "routes declare scopes"
require_literal "$SRC/application/progress.py" "text/event-stream" "SSE media type"
require_literal "$SRC/application/progress.py" "Last-Event-ID" "SSE replay header"
require_literal "$SRC/infrastructure/acl.py" "class EvidencePackAcl" "evidence ACL"
require_literal "$SRC/infrastructure/acl.py" "class GovernanceGuardAdapter" "guard ACL"
require_literal "$SRC/infrastructure/acl.py" "class ClaimVerdictAcl" "claim verdict gate"
require_literal "$SRC/infrastructure/upstream.py" "class RetrievalEvidencePacks" "stakeholder/evidence adapters"

echo ""; echo "--- Persistence, replay and wiring ---"
require_file "$SRC/infrastructure/repository/memory.py" "memory repository family"
require_literal "$SRC/infrastructure/repository/memory.py" "class InMemoryRunEventLog" "append-only run log"
require_literal "$SRC/infrastructure/repository/memory.py" "sequence=start + index" "atomic per-run ordinals"
require_file "$SRC/composition.py" "composition root"
require_method "$SRC/composition.py" build_container "build_container"
require_literal "src/shared/app.py" "negotiation_session_router" "router mounted in app shell"
require_literal "src/shared/app.py" "app.state.negotiation_session" "container exposed on app state"
require_literal ".pi/architecture/decisions/ADR-015-negotiation-session-runtime-integration.md" "**Status:** Accepted" "ADR-015 Accepted"
require_absent "$SRC" "NotImplementedError" "no NotImplementedError residue"

echo ""; echo "--- ACL purity ---"
if grep -REq "evidence_retrieval|evidence_corpus|claim_validation|stakeholder_model|governance_compliance|sqlalchemy|pgvector|numpy" "$SRC/domain" --include='*.py'; then
    fail "domain/ imports an upstream or vector/framework type"
else
    pass "domain/ imports no upstream, vector or framework type"
fi
if grep -REq "Vector\\(|pgvector|numpy|sqlalchemy|embedding_model" "$SRC/domain" --include='*.py'; then
    fail "domain/ mentions vector/embedding types"
else
    pass "domain/ vocabulary is vector-free"
fi

echo ""; echo "--- Capability proofs ---"
for test in test_aggregate_root_simulation_run.py test_owned_entities_behaviour.py test_phase_behaviour.py test_round_close_behaviour.py test_revision_behaviour.py test_one_open_position_behaviour.py test_evidence_behaviour.py test_turn_discipline_behaviour.py test_round_cap_behaviour.py test_coalition_behaviour.py test_learning_behaviour.py test_closed_immutability_behaviour.py test_replay_behaviour.py test_acl_mappers.py test_sse_behaviour.py test_negotiation_api.py; do
    found=$(find tests/unit/negotiation-session -name "$test" | head -1)
    [[ -n "$found" ]] && pass "proof $test" || fail "proof $test missing"
done
require_file "tests/integration/test_negotiation_session_runtime.py" "public-API + runtime proof"
require_literal "tests/unit/negotiation-session/replay-equivalence/test_replay_behaviour.py" "replay.state == live_final" "replay fold equality proof"

echo ""; echo "============================================"
echo "  Passed: ${PASS}  Failed: ${FAIL}"
echo "============================================"
[[ "$FAIL" -gt 0 ]] && exit 1
exit 0
