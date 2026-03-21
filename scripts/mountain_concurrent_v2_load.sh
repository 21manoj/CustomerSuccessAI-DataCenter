#!/usr/bin/env bash
#
# mountain_concurrent_v2_load.sh
#
# Runs N concurrent CS Pulse V2 manifest loads using unique company names:
#   mountain_<MountainName>  (spaces in names → underscores)
#
# Per worker:
#   1) --register --phase baseline  (new customer + onboarding + ingest + validate)
#   2) --phase intervention         (same customer_id, second window + validate)
#
# Requirements: bash, jq, python3; run from repo root OR anywhere (paths resolved via SCRIPT_DIR).
#
# Examples:
#   ./scripts/mountain_concurrent_v2_load.sh
#   WORKERS=4 BASE_URL=http://3.93.17.185 ADMIN_EMAIL=admin@cspulse.io ADMIN_PASSWORD=admin123 ./scripts/mountain_concurrent_v2_load.sh
#   VERTICAL=saas_premium SLEEP_BETWEEN_START_MS=500 ./scripts/mountain_concurrent_v2_load.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOAD_DRIVER="$REPO_ROOT/load-driver"
DEFAULT_MANIFEST="$LOAD_DRIVER/manifests/novastar_dc2s.json"

WORKERS="${WORKERS:-4}"
BASE_URL="${BASE_URL:-${CS_PULSE_BASE_URL:-http://localhost:5059}}"
ADMIN_EMAIL="${ADMIN_EMAIL:-${CS_PULSE_ADMIN_EMAIL:-admin@sacme.com}}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-${CS_PULSE_ADMIN_PASSWORD:-test123}}"
SRC_MANIFEST="${SRC_MANIFEST:-$DEFAULT_MANIFEST}"
VERTICAL="${VERTICAL:-}" 
# If empty, manifest's customer.vertical is kept. Else jq overwrite (e.g. saas_premium).
SEED_BASE="${SEED_BASE:-1000}"
SLEEP_BETWEEN_START_MS="${SLEEP_BETWEEN_START_MS:-0}"
LOG_DIR="${LOG_DIR:-$REPO_ROOT/load-driver/results/mountain_runs/$(date +%Y%m%d_%H%M%S)}"

# Popular mountain names (extend as needed; first WORKERS entries are used)
MOUNTAINS=(
  Everest
  "K2"
  Kilimanjaro
  Denali
  Matterhorn
  Fuji
  "Mont Blanc"
  Aconcagua
  Annapurna
  Rainier
  Elbrus
  Vinson
  Kosciuszko
  Olympus
  Blanc
)

PREFIX="mountain_"

mkdir -p "$LOG_DIR"

if [[ ! -f "$SRC_MANIFEST" ]]; then
  echo "Source manifest not found: $SRC_MANIFEST" >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "jq is required (brew install jq)" >&2
  exit 1
fi

mountain_slug() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_'
}

build_manifest() {
  local mountain_raw="$1"
  local out_path="$2"
  local worker_idx="$3"
  local company="${PREFIX}$(echo "$mountain_raw" | tr ' ' '_')"
  local slug
  slug="$(mountain_slug "$mountain_raw")"
  local unique_email="admin.${slug}.w${worker_idx}.$RANDOM@mountain-load.test"
  local domain="${slug}.mountain.local"

  if [[ -n "$VERTICAL" ]]; then
    jq \
      --arg name "$company" \
      --arg domain "$domain" \
      --arg email "$unique_email" \
      --arg vertical "$VERTICAL" \
      '.customer.name = $name
       | .customer.domain = $domain
       | .customer.admin_email = $email
       | .customer.vertical = $vertical' \
      "$SRC_MANIFEST" >"$out_path"
  else
    jq \
      --arg name "$company" \
      --arg domain "$domain" \
      --arg email "$unique_email" \
      '.customer.name = $name
       | .customer.domain = $domain
       | .customer.admin_email = $email' \
      "$SRC_MANIFEST" >"$out_path"
  fi
}

extract_customer_id() {
  # Matches log line: Registered: customer_id=123
  sed -n 's/.*Registered: customer_id=\([0-9][0-9]*\).*/\1/p' | tail -1
}

run_one_worker() {
  local idx="$1"
  local mountain="${MOUNTAINS[$idx]}"
  local wlog="$LOG_DIR/worker_${idx}_${PREFIX}$(mountain_slug "$mountain").log"
  local tmp_manifest="$LOG_DIR/manifest_worker_${idx}.json"
  local seed=$((SEED_BASE + idx))

  echo "=== Worker $idx: ${PREFIX}$(echo "$mountain" | tr ' ' '_') ===" | tee "$wlog"

  build_manifest "$mountain" "$tmp_manifest" "$idx"

  if [[ "$SLEEP_BETWEEN_START_MS" =~ ^[0-9]+$ ]] && [[ "$SLEEP_BETWEEN_START_MS" -gt 0 ]]; then
    sleep "$(awk "BEGIN {print $SLEEP_BETWEEN_START_MS/1000}")"
  fi

  set +e
  local out
  out="$(
    cd "$LOAD_DRIVER" && python3 cs_pulse_driver.py \
      --manifest "$tmp_manifest" \
      --register \
      --base-url "$BASE_URL" \
      --email "$ADMIN_EMAIL" \
      --password "$ADMIN_PASSWORD" \
      --seed "$seed" \
      --phase baseline \
      2>&1
  )"
  local rc1=$?
  set -e
  echo "$out" | tee -a "$wlog"
  if [[ "$rc1" -ne 0 ]]; then
    echo "Worker $idx: baseline/register FAILED (exit $rc1)" | tee -a "$wlog"
    return "$rc1"
  fi

  local cid
  cid="$(echo "$out" | extract_customer_id)"
  if [[ -z "$cid" ]]; then
    echo "Worker $idx: could not parse customer_id from output" | tee -a "$wlog"
    return 1
  fi
  echo "Worker $idx: customer_id=$cid (intervention phase next)" | tee -a "$wlog"

  set +e
  local out2
  out2="$(
    cd "$LOAD_DRIVER" && python3 cs_pulse_driver.py \
      --manifest "$tmp_manifest" \
      --customer-id "$cid" \
      --base-url "$BASE_URL" \
      --email "$ADMIN_EMAIL" \
      --password "$ADMIN_PASSWORD" \
      --seed "$seed" \
      --phase intervention \
      2>&1
  )"
  local rc2=$?
  set -e
  echo "$out2" | tee -a "$wlog"
  if [[ "$rc2" -ne 0 ]]; then
    echo "Worker $idx: intervention FAILED (exit $rc2)" | tee -a "$wlog"
    return "$rc2"
  fi

  echo "Worker $idx: OK (baseline + intervention)" | tee -a "$wlog"
  return 0
}

main() {
  echo "Log directory: $LOG_DIR"
  echo "Workers: $WORKERS  Base URL: $BASE_URL  Prefix: ${PREFIX}<mountain>"
  echo "Source manifest: $SRC_MANIFEST"

  if [[ "$WORKERS" -gt "${#MOUNTAINS[@]}" ]]; then
    echo "WORKERS=$WORKERS exceeds defined mountains (${#MOUNTAINS[@]}). Increase MOUNTAINS[] in script." >&2
    exit 1
  fi

  local pids=()
  local i
  for ((i = 0; i < WORKERS; i++)); do
    run_one_worker "$i" &
    pids+=($!)
  done

  local fail=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      fail=1
    fi
  done

  if [[ "$fail" -ne 0 ]]; then
    echo "One or more workers failed. See logs in: $LOG_DIR" >&2
    exit 1
  fi
  echo "All $WORKERS workers completed successfully."
  exit 0
}

main "$@"
