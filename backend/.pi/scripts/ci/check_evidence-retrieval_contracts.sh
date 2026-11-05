#!/usr/bin/env bash
# ============================================================================
# check_evidence-retrieval_contracts.sh — deterministic EvidenceRetrieval proofing
#
# Verifies that the frozen contract has concrete implementations, that DTOs and
# routes still exist, that corpus access stays behind published ports, and that
# the pack persistence migration and runtime wiring are present. HTTP handlers
# are concrete: this checker only requires the router file, never a handler
# interface/impl pair.
#
# Usage: bash .pi/scripts/ci/check_evidence-retrieval_contracts.sh [--help]
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

SRC="src/evidence_retrieval"
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
echo "  EvidenceRetrieval Contract Proofing"
echo "============================================"

echo ""
echo "--- Layer structure ---"
for layer in domain application infrastructure interfaces; do
    require_file "$SRC/$layer/__init__.py" "layer $layer/"
done

echo ""
echo "--- Ports and concrete implementations ---"
require_file "$SRC/domain/repositories.py" "domain repository/port contract"
for entry in \
    "EvidencePackRepository:get" \
    "EvidencePackRepository:save" \
    "EvidencePackRepository:latest_for_claim" \
    "PassageSearchPort:search" \
    "PassageSearchPort:authority_rule" \
    "PassageSearchPort:snapshot_index" \
    "PassageSearchPort:dense_search"
do
    interface="${entry%%:*}"
    method="${entry##*:}"
    require_literal "$SRC/domain/repositories.py" "class ${interface}(Protocol)" "port ${interface}"
    require_method "$SRC/domain/repositories.py" "$method" "port method ${interface}.${method}"
done

for repo in "memory.py:InMemoryEvidencePackRepository" "repository/sqlalchemy.py:SqlAlchemyEvidencePackRepository"; do
    file="${repo%%:*}"; cls="${repo##*:}"
    require_literal "$SRC/infrastructure/$file" "class ${cls}" "repository adapter ${cls}"
    for method in get save latest_for_claim; do
        require_method "$SRC/infrastructure/$file" "$method" "${cls}.${method}"
    done
done

require_literal "$SRC/infrastructure/adapters.py" "class CorpusPassageSearch" "corpus published-language adapter"
require_method "$SRC/infrastructure/adapters.py" search "CorpusPassageSearch.search"
require_method "$SRC/infrastructure/adapters.py" authority_rule "CorpusPassageSearch.authority_rule"
require_literal "$SRC/infrastructure/adapters.py" "class HashingEmbedding" "dense embedding adapter"
require_literal "$SRC/infrastructure/adapters.py" "class OverlapReranker" "reranker adapter"
require_literal "$SRC/infrastructure/adapters.py" "class RuleBasedStanceModel" "stance baseline"
require_method "$SRC/infrastructure/adapters.py" classify "RuleBasedStanceModel.classify"
require_literal "$SRC/infrastructure/adapters.py" "class StaticRetrievalReadiness" "readiness adapter"
require_method "$SRC/infrastructure/adapters.py" check "StaticRetrievalReadiness.check"
require_literal "$SRC/infrastructure/query_rewrite.py" "class GermanQueryRewrite" "query rewrite adapter"
require_literal "$SRC/domain/entities.py" "retrieval_mode" "trace records retrieval mode"
require_literal "$SRC/domain/entities.py" "index_version" "trace records index version"
require_absent_recursive "$SRC/application" "AuthorityTier.OTHER" "scoring path has no hardcoded OTHER tier"
require_file "scripts/evaluate_retrieval.py" "lexical-vs-hybrid evaluation script"
require_method "$SRC/infrastructure/query_rewrite.py" rewrite "GermanQueryRewrite.rewrite"

echo ""
echo "--- Domain services ---"
for entry in "ScoreEvidenceCandidates:score" "ApplyRecencyPolicy:apply" "ReciprocalRankFusion:fuse" "StanceClassifier:classify"; do
    cls="${entry%%:*}"; method="${entry##*:}"
    require_literal "$SRC/domain/services.py" "class ${cls}" "domain service ${cls}"
    require_method "$SRC/domain/services.py" "$method" "${cls}.${method}"
done

echo ""
echo "--- Frozen DTOs ---"
require_file "$SRC/application/dto.py" "result DTO module"
for cls in CandidateResult SearchCandidatesResult AbsenceResult TraceResult EvidencePackResult CandidateScoreResult ScoreBreakdownResult RetrievalReadiness; do
    require_literal "$SRC/application/dto.py" "class ${cls}" "DTO ${cls}"
done
require_file "$SRC/application/commands.py" "request DTO module"
for cls in SearchEvidenceCandidatesRequest AssembleEvidencePackRequest GetEvidencePackRequest GetScoreBreakdownRequest ApplyRecencyPolicyRequest; do
    require_literal "$SRC/application/commands.py" "class ${cls}" "request ${cls}"
done
require_file "$SRC/interfaces/http/schemas.py" "HTTP schema module"
for cls in SearchCandidatesBody SearchCandidatesResponse EvidencePackResponse ScoreBreakdownResponse ReweightPackBody; do
    require_literal "$SRC/interfaces/http/schemas.py" "class ${cls}" "HTTP schema ${cls}"
done

echo ""
echo "--- API surface ---"
require_file "$SRC/interfaces/http/router.py" "concrete router (no handler interface)"
for path in '"/evidence/candidates"' '"/evidence/packs"' '"/evidence/packs/{pack_id}"' '"/evidence/packs/{pack_id}/scores"' '"/evidence/packs/{pack_id}/reweight"'; do
    require_literal "$SRC/interfaces/http/router.py" "$path" "route $path"
done
require_literal "$SRC/interfaces/http/router.py" 'x-required-scope' "routes declare required scope"
require_literal "src/shared/app.py" 'evidence_retrieval_router' "router mounted in the app shell"
require_literal "src/shared/app.py" 'app.state.evidence_retrieval' "container exposed on app state"

echo ""
echo "--- Corpus boundary ---"
if ! grep -Rq --include='*.py' 'evidence_corpus.infrastructure' "$SRC"; then
    pass "retrieval never imports corpus infrastructure"
else
    fail "retrieval imports corpus infrastructure"
fi
if ! grep -Rq --include='*.py' 'evidence_corpus_indexed_passage' "$SRC"; then
    pass "retrieval never reads corpus tables directly"
else
    fail "retrieval reads corpus tables directly"
fi
if ! grep -Rq 'evidence_corpus.infrastructure' "$SRC/interfaces"; then
    pass "interfaces never import corpus infrastructure"
else
    fail "interfaces import corpus infrastructure"
fi

echo ""
echo "--- Persistence and readiness ---"
require_literal "$SRC/infrastructure/repository/models.py" 'evidence_retrieval_pack' "ORM table evidence_retrieval_pack"
require_file "migrations/versions/0201_evidence_retrieval.py" "migration 0201"
require_literal "migrations/versions/0201_evidence_retrieval.py" 'evidence_retrieval_pack' "migration owns the pack table"
require_literal "src/shared/http/health.py" 'evidence_retrieval' "readiness reports retrieval"
require_literal "src/shared/http/health.py" 'embeddings_reachable' "readiness checks embeddings"

echo ""
echo "--- Residue ---"
require_absent_recursive "$SRC" "NotImplementedError" "no NotImplementedError residue"
require_absent_recursive "$SRC" "TODO(issue" "no stale issue TODOs"
require_absent_recursive "$SRC" "TODO(wiring" "no stale wiring TODOs"

echo ""
echo "============================================"
echo "  Passed: ${PASS}  Failed: ${FAIL}"
echo "============================================"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
