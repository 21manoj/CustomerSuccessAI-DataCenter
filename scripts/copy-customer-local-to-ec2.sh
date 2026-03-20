#!/usr/bin/env bash
# Copy one customer (and related rows) from local Postgres to EC2 cspulse-postgres.
#
# Usage: ./scripts/copy-customer-local-to-ec2.sh <CUSTOMER_ID> [INSTANCE_ID]

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${REPO_ROOT}/cspulse-v6-key.pem"
BACKEND_ENV="${REPO_ROOT}/kpi-dashboard/backend/.env"
AWS_REGION="${AWS_REGION:-us-east-1}"
WORKDIR="${REPO_ROOT}/.customer_export_tmp"

CID="${1:?Usage: $0 <CUSTOMER_ID> [INSTANCE_ID]}"
INSTANCE_ID="${2:-${CSPULSE_EC2_INSTANCE_ID:-}}"

if [[ -z "$INSTANCE_ID" ]]; then
  INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cspulse-v6" "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].InstanceId' --output text --region "$AWS_REGION" 2>/dev/null | head -1)
fi
[[ -n "$INSTANCE_ID" ]] || { echo "No EC2 instance"; exit 1; }
[[ -f "$KEY_FILE" ]] || { echo "Missing $KEY_FILE"; exit 1; }
[[ -f "$BACKEND_ENV" ]] || { echo "Missing $BACKEND_ENV"; exit 1; }

DATABASE_URL=$(grep -E '^DATABASE_URL=' "$BACKEND_ENV" | sed 's/^DATABASE_URL=//' | tr -d '\r' | head -1)
if [[ ! "$DATABASE_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
  echo "Could not parse DATABASE_URL"
  exit 1
fi
L_PGUSER="${BASH_REMATCH[1]}"
L_PGPASS="${BASH_REMATCH[2]}"
L_PGHOST="${BASH_REMATCH[3]}"
L_PGPORT="${BASH_REMATCH[4]}"
L_PGNAME="${BASH_REMATCH[5]}"

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text 2>/dev/null)
[[ -n "$PUBLIC_IP" && "$PUBLIC_IP" != "None" ]] || { echo "No public IP"; exit 1; }

export PGPASSWORD="$L_PGPASS"
PSQL_L=(psql -h "$L_PGHOST" -p "$L_PGPORT" -U "$L_PGUSER" -d "$L_PGNAME" -v ON_ERROR_STOP=1)

NAME=$("${PSQL_L[@]}" -t -A -c "SELECT customer_name FROM customers WHERE customer_id = $CID;" || true)
[[ -n "$NAME" ]] || { echo "Local DB has no customer_id=$CID"; exit 1; }
unset PGPASSWORD

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

echo "=== Copy customer $CID ($NAME) → EC2 $INSTANCE_ID ($PUBLIC_IP) ==="

export_sql() {
  local table="$1"
  local where="$2"
  local f="$WORKDIR/${table}.csv"
  export PGPASSWORD="$L_PGPASS"
  "${PSQL_L[@]}" -c "\\copy (SELECT * FROM ${table} WHERE ${where}) TO '${f}' WITH (FORMAT csv, HEADER true)"
  unset PGPASSWORD
  echo "  exported ${table}"
}

# Export a custom SELECT (omit global SERIAL PKs that may collide on multi-tenant EC2).
export_sql_q() {
  local name="$1"
  local query="$2"
  local f="$WORKDIR/${name}.csv"
  export PGPASSWORD="$L_PGPASS"
  "${PSQL_L[@]}" -c "\\copy (${query}) TO '${f}' WITH (FORMAT csv, HEADER true)"
  unset PGPASSWORD
  echo "  exported ${name}"
}

ACCT="(SELECT account_id FROM accounts WHERE customer_id = $CID)"

echo "1. Exporting from local..."
export_sql customers "customer_id = $CID"
export_sql_q users "SELECT customer_id, user_name, email, password_hash, active, last_login, uuid, customer_uuid, created_at, updated_at, vertical, role, allowed_account_ids, allowed_customer_ids, expires_at, is_contractor FROM users WHERE customer_id = $CID"
export_sql_q customer_configs "SELECT customer_id, kpi_upload_mode, category_weights, master_file_name, openai_api_key_encrypted, openai_api_key_updated_at, vertical, dc2s_pillar_weights, dc2s_enabled_kpis, dc2s_kpi_overrides, dc2s_kpi_weights FROM customer_configs WHERE customer_id = $CID"
export_sql_q feature_toggles "SELECT customer_id, feature_name, enabled, config, description, created_at, updated_at FROM feature_toggles WHERE customer_id = $CID"
export_sql_q playbook_triggers "SELECT customer_id, playbook_type, trigger_config, auto_trigger_enabled, last_evaluated, last_triggered, trigger_count, created_at, updated_at, playbook_id, trigger_conditions FROM playbook_triggers WHERE customer_id = $CID"
export_sql accounts "customer_id = $CID"
export_sql_q products "SELECT account_id, customer_id, product_name, product_sku, product_type, revenue, status, created_at, updated_at FROM products WHERE customer_id = $CID"
export_sql_q agent_memory "SELECT customer_id, account_id, agent_id, memory_type, scope, namespace, key, content, metadata, embedding_id, importance, access_count, last_accessed, created_at, expires_at, is_archived FROM agent_memory WHERE customer_id = $CID"
export_sql_q health_scores "SELECT account_id, measurement_month, health_score, health_status, trend, change_from_last_month, contributing_pillars, pillar_weights, calculated_at FROM health_scores WHERE account_id IN ${ACCT}"
export_sql_q health_trends "SELECT account_id, customer_id, month, year, overall_health_score, product_usage_score, support_score, customer_sentiment_score, business_outcomes_score, relationship_strength_score, total_kpis, valid_kpis, created_at, updated_at FROM health_trends WHERE account_id IN ${ACCT}"
export_sql_q pillar_scores "SELECT account_id, measurement_month, pillar_code, pillar_score, pillar_status, contributing_kpis, kpi_weights, calculated_at FROM pillar_scores WHERE account_id IN ${ACCT}"
export_sql qualitative_signals "account_id IN ${ACCT}"
export_sql_q dc2s_kpis "SELECT account_id, kpi_code, value, target, pillar, weight, status, measured_at, created_at FROM dc2s_kpis WHERE account_id IN ${ACCT}"
export_sql context_nodes "customer_id = $CID"
export_sql_q context_edges "SELECT customer_id, from_node_id, to_node_id, edge_type, lag_days, weight, confidence, revenue_impact, revenue_impact_type, properties, source_platform, created_by, occurred_at, expires_at, created_at FROM context_edges WHERE customer_id = $CID"

echo "2. Pack and upload..."
export COPYFILE_DISABLE=1 2>/dev/null || true
tar -czf "$WORKDIR/cust_${CID}_data.tgz" -C "$WORKDIR" \
  customers.csv users.csv customer_configs.csv feature_toggles.csv playbook_triggers.csv \
  accounts.csv products.csv agent_memory.csv health_scores.csv health_trends.csv pillar_scores.csv \
  qualitative_signals.csv dc2s_kpis.csv context_nodes.csv context_edges.csv

scp -o StrictHostKeyChecking=no -i "$KEY_FILE" "$WORKDIR/cust_${CID}_data.tgz" "ec2-user@${PUBLIC_IP}:/home/ec2-user/"

# Remote apply: expand CID into SQL here (local shell)
REMOTE_SH="${WORKDIR}/remote_apply_${CID}.sh"
# shellcheck disable=SC2016
cat > "$REMOTE_SH" <<REMOTEEOF
#!/usr/bin/env bash
set -euo pipefail
CID=${CID}
cd /home/ec2-user
rm -rf cust_\${CID}_import && mkdir -p cust_\${CID}_import
tar -xzf cust_\${CID}_data.tgz -C cust_\${CID}_import
sudo docker cp cust_\${CID}_import/. cspulse-postgres:/tmp/cust_\${CID}_import/

sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=0 -c "
DELETE FROM playbook_step_log WHERE execution_id IN (SELECT execution_id FROM playbook_executions WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID}));
DELETE FROM playbook_executions WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM playbook_reports WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM account_notes WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM account_snapshots WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM action_economics WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM dc2s_kpis WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM journey_data WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM kpi_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM kpi_time_series WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM kpi_uploads WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM kpis WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM product_trends WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM context_edges WHERE customer_id = ${CID};
DELETE FROM context_nodes WHERE customer_id = ${CID};
DELETE FROM qualitative_signals WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM pillar_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM health_trends WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM health_scores WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id = ${CID});
DELETE FROM products WHERE customer_id = ${CID};
DELETE FROM agent_memory WHERE customer_id = ${CID};
DELETE FROM accounts WHERE customer_id = ${CID};
DELETE FROM feature_toggles WHERE customer_id = ${CID};
DELETE FROM playbook_triggers WHERE customer_id = ${CID};
DELETE FROM customer_configs WHERE customer_id = ${CID};
DELETE FROM users WHERE customer_id = ${CID};
DELETE FROM customer_contacts WHERE customer_id = ${CID};
DELETE FROM portfolio_memberships WHERE customer_id = ${CID};
DELETE FROM activity_logs WHERE customer_id = ${CID};
DELETE FROM rag_query_log WHERE customer_id = ${CID};
DELETE FROM rag_knowledge_base WHERE customer_id = ${CID};
DELETE FROM customers WHERE customer_id = ${CID};
"

sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy customers FROM '/tmp/cust_${CID}_import/customers.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy users (customer_id, user_name, email, password_hash, active, last_login, uuid, customer_uuid, created_at, updated_at, vertical, role, allowed_account_ids, allowed_customer_ids, expires_at, is_contractor) FROM '/tmp/cust_${CID}_import/users.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy customer_configs (customer_id, kpi_upload_mode, category_weights, master_file_name, openai_api_key_encrypted, openai_api_key_updated_at, vertical, dc2s_pillar_weights, dc2s_enabled_kpis, dc2s_kpi_overrides, dc2s_kpi_weights) FROM '/tmp/cust_${CID}_import/customer_configs.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy feature_toggles (customer_id, feature_name, enabled, config, description, created_at, updated_at) FROM '/tmp/cust_${CID}_import/feature_toggles.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy playbook_triggers (customer_id, playbook_type, trigger_config, auto_trigger_enabled, last_evaluated, last_triggered, trigger_count, created_at, updated_at, playbook_id, trigger_conditions) FROM '/tmp/cust_${CID}_import/playbook_triggers.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy accounts FROM '/tmp/cust_${CID}_import/accounts.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy products (account_id, customer_id, product_name, product_sku, product_type, revenue, status, created_at, updated_at) FROM '/tmp/cust_${CID}_import/products.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy agent_memory (customer_id, account_id, agent_id, memory_type, scope, namespace, key, content, metadata, embedding_id, importance, access_count, last_accessed, created_at, expires_at, is_archived) FROM '/tmp/cust_${CID}_import/agent_memory.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy health_scores (account_id, measurement_month, health_score, health_status, trend, change_from_last_month, contributing_pillars, pillar_weights, calculated_at) FROM '/tmp/cust_${CID}_import/health_scores.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy health_trends (account_id, customer_id, month, year, overall_health_score, product_usage_score, support_score, customer_sentiment_score, business_outcomes_score, relationship_strength_score, total_kpis, valid_kpis, created_at, updated_at) FROM '/tmp/cust_${CID}_import/health_trends.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy pillar_scores (account_id, measurement_month, pillar_code, pillar_score, pillar_status, contributing_kpis, kpi_weights, calculated_at) FROM '/tmp/cust_${CID}_import/pillar_scores.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy qualitative_signals FROM '/tmp/cust_${CID}_import/qualitative_signals.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy dc2s_kpis (account_id, kpi_code, value, target, pillar, weight, status, measured_at, created_at) FROM '/tmp/cust_${CID}_import/dc2s_kpis.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy context_nodes FROM '/tmp/cust_${CID}_import/context_nodes.csv' WITH (FORMAT csv, HEADER true)"
sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c "\\copy context_edges (customer_id, from_node_id, to_node_id, edge_type, lag_days, weight, confidence, revenue_impact, revenue_impact_type, properties, source_platform, created_by, occurred_at, expires_at, created_at) FROM '/tmp/cust_${CID}_import/context_edges.csv' WITH (FORMAT csv, HEADER true)"

sudo docker exec cspulse-postgres rm -rf /tmp/cust_${CID}_import
rm -rf cust_${CID}_import cust_${CID}_data.tgz
REMOTEEOF

chmod +x "$REMOTE_SH"
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" "$REMOTE_SH" "ec2-user@${PUBLIC_IP}:/home/ec2-user/remote_apply_${CID}.sh"
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" bash "/home/ec2-user/remote_apply_${CID}.sh"

echo "3. Verify on EC2..."
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" \
  "sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -t -A -c \"SELECT customer_id, customer_name FROM customers WHERE customer_id = $CID;\""

echo "=== Done. customer $CID copied to EC2 ==="
rm -rf "$WORKDIR"
