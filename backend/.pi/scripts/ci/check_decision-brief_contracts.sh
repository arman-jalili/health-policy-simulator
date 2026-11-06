#!/usr/bin/env bash
# Deterministic proofing for the decision-brief contract (epic #330, issue #347).
#
# Asserts the frozen surface structurally: layer files, enums, aggregate gates, error codes,
# events, routes/scopes, wire schema, composition gates, runtime binding and the documented
# deferral of upstream ACL adapters. No LLM, no network, no test-suite run.
set -uo pipefail
PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); }
fail() { FAIL=$((FAIL+1)); echo "  FAIL: $1"; }
require_file() { [[ -f "$1" ]] && pass || fail "missing file $1"; }
require_literal() { grep -qF "$2" "$1" 2>/dev/null && pass || fail "$3 ($2 in $1)"; }
forbid_literal() { ! grep -qF "$2" "$1" 2>/dev/null && pass || fail "$3 ($2 in $1)"; }

SRC="src/decision_brief"

# ── Layers ──
for f in domain/values.py domain/entities.py domain/projections.py domain/decision_brief.py \
         domain/errors.py domain/events.py domain/repositories.py domain/services.py \
         application/commands.py application/dto.py application/ports.py application/services.py \
         infrastructure/acl.py infrastructure/failclosed.py infrastructure/projection.py \
         infrastructure/runtime.py infrastructure/repository/ports.py \
         infrastructure/repository/memory.py \
         interfaces/renderer.py interfaces/http/router.py interfaces/http/schemas.py \
         interfaces/http/deps.py composition.py; do
  require_file "$SRC/$f"
done

# ── Eight sections and evidence vocabulary ──
for kind in question_summary actors_involved negotiation_history conflict_analysis \
            compromise_proposals consensus_analysis open_disputes impact; do
  require_literal "$SRC/domain/values.py" "\"$kind\"" "section kind $kind"
done
for status in evidenced narrative unsupported; do
  require_literal "$SRC/domain/values.py" "\"$status\"" "evidence status $status"
done
for state in draft validating blocked published superseded; do
  require_literal "$SRC/domain/values.py" "\"$state\"" "brief status $state"
done
for outcome in recommendation blocked open_dispute; do
  require_literal "$SRC/domain/values.py" "\"$outcome\"" "outcome kind $outcome"
done

# ── Aggregate gates ──
for method in publish assert_statement_evidence assert_rejected_proposals_disclosed \
              resolve_citations assert_immutable supersede_by missing_sections \
              unresolved_citations citation_count; do
  require_literal "$SRC/domain/decision_brief.py" "def $method" "aggregate $method"
done
require_literal "$SRC/domain/decision_brief.py" "_FrozenSections" "immutable section map"
require_literal "$SRC/domain/services.py" "class SectionAssembler" "section assembler"
require_literal "$SRC/domain/services.py" "class ReproductionCheck" "reproduction checker"
require_literal "$SRC/domain/services.py" "class OutcomeHonestyCheck" "outcome honesty check"
require_literal "$SRC/domain/services.py" "SERVICE_CLASSIFICATION" "service classification"

# ── Error contract ──
for code in INCOMPLETE_BRIEF UNRESOLVED_CITATION DISCLOSURE_MISSING STATEMENT_WITHOUT_CITATION \
            BLOCKED_OUTCOME_MISRENDERED PUBLISHED_BRIEF_IMMUTABLE BRIEF_NOT_PUBLISHED \
            BRIEF_REPRODUCTION_MISMATCH BRIEF_NOT_FOUND BRIEF_GATE_UNAVAILABLE \
            BRIEF_SOURCE_INCOMPLETE BRIEF_VERSION_CONFLICT; do
  require_literal "$SRC/domain/errors.py" "$code" "error $code"
done

# ── Events ──
for event in DecisionBriefPublished DecisionBriefVersioned CitationResolutionFailed \
             RejectedProposalDisclosed BriefBlockedByMissingDisclosure; do
  require_literal "$SRC/domain/events.py" "class $event" "event $event"
done

# ── Application contracts ──
for service in PublishDecisionBrief VersionDecisionBrief GetDecisionBrief ListBriefVersions \
               ListCitations; do
  require_literal "$SRC/application/services.py" "class $service" "service $service"
  require_literal "$SRC/application/services.py" "def collaborators" "collaborators for $service"
done
for port in CitationResolver ProvenanceDisclosureGate RunHistorySource ConsensusSource Clock \
            UnitOfWork IdFactory EventPublisher; do
  require_literal "$SRC/application/ports.py" "class $port(Protocol)" "port $port"
done
for stub in "PublishDecisionBrief.execute is implemented by" \
            "VersionDecisionBrief.execute is implemented by"; do
  forbid_literal "$SRC/application/services.py" "$stub" "stub marker"
done

# ── Interfaces ──
for path in '/runs/{run_id}/brief' '/briefs/{brief_id}' '/runs/{run_id}/briefs' \
            '/briefs/{brief_id}:version' '/briefs/{brief_id}/citations'; do
  require_literal "$SRC/interfaces/http/router.py" "$path" "route $path"
done
for scope in briefs:publish runs:read; do
  require_literal "$SRC/interfaces/http/router.py" "$scope" "scope $scope"
done
for field in brief_id run_id status version sections rejected_proposals outcomes disclaimer \
             citation_count schema_version; do
  require_literal "$SRC/interfaces/http/schemas.py" "$field" "document field $field"
done
for field in text model_reference prompt_version; do
  require_literal "$SRC/interfaces/http/schemas.py" "$field" "disclaimer field $field"
done
require_literal "$SRC/interfaces/renderer.py" 'BRIEF_DOCUMENT_SCHEMA_VERSION' "document schema version"
require_literal "$SRC/interfaces/renderer.py" "def brief_document" "document mapping"
forbid_literal "$SRC/interfaces/renderer.py" "JsonBriefRenderer.render is implemented by" \
  "renderer stub marker"

# ── Composition and runtime binding ──
require_literal "$SRC/composition.py" "def build_container" "composition factory"
for port in briefs history consensus citations provenance projection renderer disclaimer \
            events clock ids uow; do
  require_literal "$SRC/composition.py" "$port:" "composition port $port"
done
require_literal "src/shared/app.py" "build_decision_brief_container" "runtime composition"
require_literal "src/shared/app.py" "decision_brief_router" "runtime router"
require_literal "src/shared/app.py" "app.state.decision_brief" "runtime container binding"
require_literal "$SRC/infrastructure/failclosed.py" "class UnwiredProvenanceGate" "fail-closed gate"
require_literal "$SRC/infrastructure/projection.py" "class BriefProjectionAdapter" "real projection"

# ── Documented deferral: no undocumented stubs ──
STUBS=$(grep -R "NotImplementedError" -n "$SRC" --include='*.py' | grep -v "infrastructure/acl.py" || true)
[[ -z "$STUBS" ]] && pass || fail "undocumented NotImplementedError outside infrastructure/acl.py: $STUBS"
require_file "docs/contracts-decision-brief.md"
require_file ".pi/architecture/DEFERRED.md"
require_literal ".pi/architecture/DEFERRED.md" "D-007 — DecisionBrief upstream bindings" "deferral record"

# ── Test evidence for every acceptance criterion ──
TESTS="tests/unit/decision-brief"
for proof in "eight-sections:IncompleteBrief" "citation-gate:UnresolvedCitation" \
             "rejected-proposals:DisclosureMissing" "disclaimer:simulation_disclaimer" \
             "statement-evidence:StatementWithoutCitation" \
             "immutability:PublishedBriefIsImmutable" "lineage:BriefVersionConflict" \
             "reproduction:BriefReproductionMismatch" \
             "blocked-outcome-honesty:BlockedOutcomeMisrendered" \
             "probabilistic-disclaimer:model_reference" "wiring:decision_brief"; do
  dir="${proof%%:*}"; needle="${proof##*:}"
  grep -Rq "$needle" "$TESTS/$dir" 2>/dev/null && pass || fail "AC proof $dir ($needle)"
done

echo "============================================"
echo "  Passed: $PASS  Failed: $FAIL"
echo "============================================"
[[ $FAIL -eq 0 ]]
