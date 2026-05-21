#!/usr/bin/env bash
# Step 7 acceptance: HTTP dashboard checks + optional persona grading in Docker.
#
# Usage (from repo root):
#   cp scripts/.env.acceptance.example scripts/.env.acceptance
#   # edit scripts/.env.acceptance (ANTHROPIC_API_KEY, base URL, etc.)
#   ./scripts/run_acceptance_ec2.sh
#
# Options via environment:
#   ACCEPTANCE_SKIP_HTTP=1       Skip verify_executive_phases_ec2.py
#   ACCEPTANCE_RUN_PERSONA=1     Run persona grading in container (needs API key)
#   ACCEPTANCE_SEED_VPCS=1       docker exec seed_vpcs_demo_334.py first
#   ACCEPTANCE_SUITE=all|cfo,cro,...  Passed to verify script

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

ENV_FILE="${ACCEPTANCE_ENV_FILE:-$REPO_ROOT/scripts/.env.acceptance}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
  echo "Loaded $ENV_FILE"
else
  echo "No $ENV_FILE — using defaults / existing shell env"
fi

SUITE="${ACCEPTANCE_SUITE:-all}"
CUSTOMER_ID="${ACCEPTANCE_CUSTOMER_ID:-334}"
PERSONA_SHOTS="${ACCEPTANCE_PERSONA_SHOTS:-3}"
PERSONAS="${ACCEPTANCE_PERSONAS:-cro,cfo,vpcs}"
MIN_GRADE="${ACCEPTANCE_MIN_GRADE_NUMERIC:-0}"
OUTPUT_DIR="${ACCEPTANCE_OUTPUT_DIR:-$REPO_ROOT/scripts/datasets}"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUTPUT_DIR"
FAILED=0

_run_http() {
  if [[ "${ACCEPTANCE_SKIP_HTTP:-0}" == "1" ]]; then
    echo "Skipping HTTP acceptance (ACCEPTANCE_SKIP_HTTP=1)"
    return 0
  fi
  echo ""
  echo "=== HTTP acceptance (user-perspective) suite=$SUITE ==="
  python3 "$REPO_ROOT/scripts/verify_executive_phases_ec2.py" --suite "$SUITE" || FAILED=1
}

_resolve_container() {
  if [[ -n "${CSPULSE_CONTAINER:-}" ]]; then
    echo "$CSPULSE_CONTAINER"
    return
  fi
  local name
  name="$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E 'cspulse-platform|platform' | head -1 || true)"
  if [[ -z "$name" ]]; then
    name="$(docker ps --format '{{.Names}}' 2>/dev/null | head -1 || true)"
  fi
  echo "$name"
}

_run_seed() {
  if [[ "${ACCEPTANCE_SEED_VPCS:-0}" != "1" ]]; then
    return 0
  fi
  local ctr
  ctr="$(_resolve_container)"
  if [[ -z "$ctr" ]]; then
    echo "WARN: ACCEPTANCE_SEED_VPCS=1 but no Docker container found — skip seed"
    return 0
  fi
  echo ""
  echo "=== Seed VPCS demo data (customer $CUSTOMER_ID) in $ctr ==="
  docker exec "$ctr" python3 /app/backend/scripts/seed_vpcs_demo_334.py || FAILED=1
}

_run_persona() {
  if [[ "${ACCEPTANCE_RUN_PERSONA:-0}" != "1" ]]; then
    echo ""
    echo "Persona grading skipped (set ACCEPTANCE_RUN_PERSONA=1 to enable)"
    return 0
  fi
  if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "ERROR: ACCEPTANCE_RUN_PERSONA=1 requires ANTHROPIC_API_KEY"
    FAILED=1
    return 1
  fi

  local ctr
  ctr="$(_resolve_container)"
  if [[ -z "$ctr" ]]; then
    echo "ERROR: No running platform container for persona grading"
    FAILED=1
    return 1
  fi

  local out_in_container="/app/backend/scripts/datasets/persona_grades_${CUSTOMER_ID}_${STAMP}.json"
  local out_host="$OUTPUT_DIR/persona_grades_${CUSTOMER_ID}_${STAMP}.json"

  echo ""
  echo "=== Persona grading in $ctr (customer=$CUSTOMER_ID shots=$PERSONA_SHOTS personas=$PERSONAS) ==="

  docker exec "$ctr" mkdir -p /app/backend/scripts/datasets 2>/dev/null || true

  docker exec \
    -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
    -e DATABASE_URL="${DATABASE_URL:-}" \
    "$ctr" \
    python3 -m tests.persona_grading.runner \
      --customer "$CUSTOMER_ID" \
      --shots "$PERSONA_SHOTS" \
      --personas "$PERSONAS" \
      --output "$out_in_container" || { FAILED=1; return 1; }

  docker cp "$ctr:$out_in_container" "$out_host" 2>/dev/null || true
  echo "Persona results: $out_host"

  if [[ "$MIN_GRADE" != "0" && "$MIN_GRADE" != "0.0" ]]; then
    python3 - "$out_host" "$MIN_GRADE" <<'PY'
import json, sys
path, min_grade = sys.argv[1], float(sys.argv[2])
with open(path) as f:
    data = json.load(f)
summary = data.get("summary") or {}
failed = []
for persona, info in summary.items():
    num = info.get("avg_numeric")
    if num is None:
        continue
    if num < min_grade:
        failed.append((persona, info.get("avg_grade"), num))
if failed:
    print("GRADE GATE FAIL (min %.2f):" % min_grade)
    for p, letter, num in failed:
        print(f"  {p}: {letter} ({num})")
    sys.exit(1)
print("GRADE GATE PASS (all personas >= %.2f)" % min_grade)
PY
    if [[ $? -ne 0 ]]; then
      FAILED=1
    fi
  fi
}

_run_seed
_run_http
_run_persona

echo ""
if [[ "$FAILED" -eq 0 ]]; then
  echo "ACCEPTANCE OVERALL: PASS"
  exit 0
else
  echo "ACCEPTANCE OVERALL: FAIL"
  exit 1
fi
