#!/usr/bin/env bash
# Pre-commit / CI check — ban direct `client.messages.create` /
# `chat.completions.create` calls outside the llm_call() wrapper.
#
# Background: Apr 20, 2026 — 6 production files were making raw LLM
# SDK calls without invoking record_usage(). Invisible Anthropic spend.
# The llm_call() wrapper in utils/llm_budget_controller.py forces
# record_usage on every exit path; this hook ensures new LLM call
# sites go through it.
#
# Exit 0 = clean. Exit 1 = blocked (raw SDK call found).
#
# Usage:
#   bash scripts/check_llm_wrapper.sh
#
# Bypass (for emergency unblock): LLM_WRAPPER_CHECK_SKIP=1
#
# Approved-exceptions list: utils/llm_budget_controller.py (the wrapper
# itself) + utils/signal_analyst.py (the original signal_analyst
# library with its own tight cost-tracking pattern, audited Apr 20).

set -e

if [[ "${LLM_WRAPPER_CHECK_SKIP:-0}" == "1" ]]; then
  echo "LLM wrapper check skipped (LLM_WRAPPER_CHECK_SKIP=1)"
  exit 0
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="${REPO_ROOT}/kpi-dashboard/backend"

if [[ ! -d "$BACKEND" ]]; then
  echo "Backend dir not found: $BACKEND"
  exit 1
fi

# Approved direct-call sites (historical, audited, tracking intact).
# Any file in this list MAY call messages.create / chat.completions.create
# directly without going through llm_call() — but it MUST still invoke
# record_usage() adjacent to the call.
#
# Grandfathered as of Apr 21, 2026. NEW files SHOULD use
# utils.llm_budget_controller.llm_call() instead of appending to this list.
# Before adding an entry here, audit the file for adjacent record_usage()
# calls on both success and failure paths — if those are missing, fix the
# file or wrap it in llm_call() instead of grandfathering.
APPROVED=(
  'utils/llm_budget_controller.py'       # the wrapper itself
  'utils/signal_analyst.py'              # original signal_analyst library
  'llm/context_helpers.py'               # audited Apr 20, tracks on both paths
  'llm/tier1_inference.py'               # audited Apr 20 (MOD-007)
  'llm/action_plan_generator.py'         # audited Apr 20
  'ask_ai_endpoint.py'                   # 2 call sites, tracks on both
  'enhanced_rag_qdrant.py'               # tracks via _budget_record
  'simple_working_rag.py'                # audited Apr 20
  'agents/signal_analyst_agent.py'       # migrated Apr 20 to record_usage
  'agents/onboarding_agent.py'           # migrated Apr 20 to record_usage
  'agents/claude_signal_analyst_agent.py' # migrated Apr 20 to record_usage
  'agents/decision_matrix.py'            # audited Apr 20
  'enhanced_rag_temporal.py'             # tracks via _budget_record
  'enhanced_rag_system.py'               # tracks via _budget_record
  'executive_dashboard_api.py'           # tracks via _budget_record
  'signal_engine/enrichment.py'          # audited Apr 20
  'governance_rag_api.py'                # tracks via _budget_record
  'enhanced_rag_historical.py'           # tracks via _budget_record
  'direct_rag_api.py'                    # tracks via _budget_record
  'signal_analyst_v2_openai.py'          # tracks via _budget_record
  'simple_rag_system.py'                 # tracks via _budget_record
  'enhanced_rag_with_mcp.py'             # tracks via _budget_record
  'enhanced_rag_openai.py'               # tracks via _budget_record
  'working_rag_system.py'                # tracks via _budget_record
)

# Search for direct SDK calls in production Python files.
# Exclude: tests, vertical-customer directories, _template, week2_exercise,
#          plus the approved list above.
matches=$(grep -rn --include='*.py' -E \
    '(client|openai_client|anthropic_client|openai|anthropic)\.(messages\.create|chat\.completions\.create)' \
    "$BACKEND" \
    2>/dev/null \
  | grep -v '/verticals/customer[0-9]' \
  | grep -v '/test_' \
  | grep -v '/tests/' \
  | grep -v '/_template/' \
  | grep -v '/week2_exercise' \
  | grep -v 'cost_tracker_deprecated' \
  || true)

# Filter out approved exceptions.
violations=""
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  keep=1
  for approved_path in "${APPROVED[@]}"; do
    if [[ "$line" == *"$approved_path"* ]]; then
      keep=0
      break
    fi
  done
  if [[ "$keep" == "1" ]]; then
    violations="${violations}${line}"$'\n'
  fi
done <<< "$matches"

if [[ -n "$(echo -n "$violations" | tr -d '[:space:]')" ]]; then
  echo "❌ LLM wrapper check: direct messages.create / chat.completions.create calls found outside llm_call() wrapper."
  echo ""
  echo "Offending lines:"
  echo "$violations"
  echo ""
  echo "Fix: wrap the call via utils.llm_budget_controller.llm_call(client, customer_id, module, model, ...)"
  echo "     OR add the file path to APPROVED list in scripts/check_llm_wrapper.sh with justification."
  echo ""
  echo "Bypass (use sparingly): LLM_WRAPPER_CHECK_SKIP=1"
  exit 1
fi

echo "✅ LLM wrapper check: no unauthorized direct SDK calls."
exit 0
