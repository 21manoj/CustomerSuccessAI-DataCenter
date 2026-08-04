# CS Pulse — EC2 runtime access (need-to-know)

**Audience:** Developers validating dashboard numbers and tracing data pipelines **without** a full git clone.

**Model:** SSH to EC2 → explore the **running stack** (containers). You get tenant-scoped data, pipeline source that ships in the image, and audit scripts — not the entire monorepo, deploy keys, or host git checkout.

> **Companion doc:** `KT_dashboard_data_lineage_and_evals.md` (same folder) — lineage tables, persona metrics, eval commands. Read **this doc first** for *how to access*; read the KT doc for *what each number means*.

---

## What you receive (need-to-know)

| Item | Purpose |
|------|---------|
| **SSH private key** | `ec2-user@<EC2_HOST>` only |
| **Demo tenant login** | UI + API for customer **336** (Predictor v3 SaaS demo) |
| **Runtime kit folder** on EC2 | `~/cspulse-runtime-kit/` — docs + helper scripts (no git) |
| **This doc + KT doc** | Copied into runtime kit on each admin sync |

## What you do **not** receive

| Blocked | Why |
|---------|-----|
| GitHub / git clone | Full repo includes infra, secrets patterns, unrelated verticals |
| `~/CustomerSuccessAI-DataCenter` on EC2 host | Deploy checkout — operators only |
| Production `.env` / API keys | Use demo tenant credentials provided separately |
| AWS console / ECR | Not required for validation work |

---

## Connect

```bash
# From your laptop
export CSPULSE_SSH_KEY_FILE=~/.ssh/cspulse-v6-key.pem
export CSPULSE_EC2_HOST=ec2-user@3.94.106.197

ssh -i "$CSPULSE_SSH_KEY_FILE" "$CSPULSE_EC2_HOST"
```

On the EC2 host, **all product logic lives in Docker** — do not expect a dev tree on the host.

```bash
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
# cspulse-platform   — Flask + React + MCP + load-driver
# cspulse-postgres   — PostgreSQL
```

---

## Step 1 — Runtime map (inside container)

Shows **allowlisted** paths for pipelines, wizards, and tenant 336 data:

```bash
sudo docker exec -e CUSTOMER_ID=336 cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py map
```

**process_data order** (same as production ingest):

```bash
sudo docker exec cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py pipeline
```

Read source (examples):

```bash
sudo docker exec -it cspulse-platform bash
less /app/backend/mcp_server/process_data_pipeline.py
less /app/load-driver/scenarios/scenario_manifest.py
less /app/backend/utils/context_graph.py
```

> **Note:** Most backend modules are Cython-compiled (`.so`) in production images. `.py` sources are often still present for inspection; runtime behavior always wins over stale source.

---

## Step 2 — Tenant data on disk (ingested CSV pack)

After upload + `process_data`, source CSVs for customer 336:

```text
/app/backend/verticals/customer336-saas_premium/data/*.csv
```

```bash
# List files + row counts
sudo docker exec -e CUSTOMER_ID=336 cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py csv-ls

# Preview a file
sudo docker exec -e CUSTOMER_ID=336 cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py csv-head qualitative_signals.csv --lines 10
```

**Manifest** (generator spec, not ingested):

```text
/app/load-driver/manifests/predictor_v3_demo_saas_cust336.json
```

```bash
sudo docker exec cspulse-platform \
  python3 -c "import json; print(json.dumps(json.load(open('/app/load-driver/manifests/predictor_v3_demo_saas_cust336.json')), indent=2)[:4000])"
```

---

## Step 3 — Live API / dashboard numbers (no laptop scripts)

Uses the in-process Flask test client (same code path as production):

```bash
sudo docker exec -e CUSTOMER_ID=336 \
  -e AUDIT_EMAIL='admin@predictor-v3-demo.io' \
  -e AUDIT_PASSWORD='<provided>' \
  cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py endpoints
```

Full parity audit (CRO/CFO/CEO, ARR, revenue@risk, playbook checks):

```bash
sudo docker exec -e CUSTOMER_ID=336 \
  -e AUDIT_EMAIL='admin@predictor-v3-demo.io' \
  -e AUDIT_PASSWORD='<provided>' \
  cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py audit
```

JSON on stdout — save locally:

```bash
ssh -i "$CSPULSE_SSH_KEY_FILE" "$CSPULSE_EC2_HOST" \
  "sudo docker exec -e CUSTOMER_ID=336 -e AUDIT_EMAIL='...' -e AUDIT_PASSWORD='...' cspulse-platform \
   python3 /app/backend/scripts/runtime_explorer.py audit" \
  > cust336_audit.json
```

**UI** (browser): `http://<EC2_HOST>/saas-dashboard/cro` (and `/cfo`, `/vpcs`, `/csm`) — log in with provided demo user; tenant 336 is pre-selected or set via admin.

---

## Step 4 — Export DB truth to your laptop

Export selected tables + manifest to `/tmp/runtime_export/336/` inside the container:

```bash
sudo docker exec -e CUSTOMER_ID=336 -e RUNTIME_EXPORT_DIR=/tmp/runtime_export/336 cspulse-platform \
  python3 /app/backend/scripts/runtime_explorer.py export-db \
  --types accounts,signals,kpi_measurements,outcomes
```

Pull to laptop:

```bash
# On EC2
sudo docker cp cspulse-platform:/tmp/runtime_export/336 /tmp/cust336_export
sudo chown -R ec2-user:ec2-user /tmp/cust336_export

# On laptop
scp -r -i "$CSPULSE_SSH_KEY_FILE" \
  "$CSPULSE_EC2_HOST:/tmp/cust336_export" ./cust336_export
```

Compare layers: **manifest** → **ingested CSV** (`csv-ls`) → **export-db** → **audit/endpoints** JSON.

---

## Step 5 — PostgreSQL (optional, read-only)

```bash
sudo docker exec -it cspulse-postgres psql -U cspulse -d cspulse
```

Example (customer 336):

```sql
SELECT COUNT(*), ROUND(SUM(revenue)::numeric, 2) FROM accounts WHERE customer_id = 336;

SELECT node_type, COUNT(*) FROM context_nodes WHERE customer_id = 336 GROUP BY 1;

SELECT COUNT(*), status FROM predictor_calibration
  WHERE customer_id = 336 GROUP BY 2;
```

Use SQL when you need row-level proof beyond CSV export.

---

## Need-to-know path allowlist (container)

| Topic | Path |
|-------|------|
| Synthetic data engine | `/app/load-driver/scenarios/scenario_manifest.py` |
| Manifest 336 | `/app/load-driver/manifests/predictor_v3_demo_saas_cust336.json` |
| Ingestion orchestration | `/app/backend/mcp_server/cs_pulse_onboarding.py` |
| **process_data** stages | `/app/backend/mcp_server/process_data_pipeline.py` |
| Wizards A–D | `/app/backend/wizards/wizard_*.py` |
| Health math | `/app/backend/utils/score_calculator.py` |
| Revenue @ risk | `/app/backend/utils/context_graph.py` |
| Executive APIs | `/app/backend/executive_dashboard_api.py` |
| Predictor v3 | `/app/backend/predictor/inference.py`, `wizard_d_predictor_calibrator.py` |
| Ingested CSVs | `/app/backend/verticals/customer336-saas_premium/data/` |
| Runtime tools | `/app/backend/scripts/runtime_explorer.py`, `ec2_persona_audit.py` |

**Ignore** hundreds of `verticals/customer290-*/journey/` trees — historical copies. For 336, only `customer336-saas_premium/data/` matters on disk.

---

## Runtime kit on EC2 host (docs only)

Admins sync a small bundle — no git:

```bash
# Run by operator from laptop (after doc changes)
./scripts/sync_ec2_runtime_kit.sh
```

Contents on EC2: `~/cspulse-runtime-kit/docs/` (this file + KT doc), `README.txt`.

---

## Suggested first-day workflow

1. SSH → `docker ps` → `runtime_explorer.py map`
2. `csv-ls` + `csv-head qualitative_signals.csv`
3. `runtime_explorer.py audit` → save JSON
4. Open CRO/CFO in browser; compare **Revenue at Risk**, **NRR** to audit JSON
5. Read `process_data_pipeline.py` + `context_graph.py` for the metric you traced
6. `export-db` → scp → spreadsheet diff vs ingested CSV
7. Read KT doc §3f worked example for the same metric

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `runtime_explorer.py` not found | Platform image predates kit — ask operator to deploy or `docker cp` script into container |
| Empty `verticals/customer336-*/data` | `process_data` not run for 336 — operator runs ingest |
| Audit login failed | Check `AUDIT_EMAIL` / `AUDIT_PASSWORD` for tenant 336 |
| CRO ≠ CFO on revenue fields | Bug — file with audit JSON |
| Predictor NRR missing | Wizard D calibration — check `predictor_calibration` in psql |

---

## For operators (syncing the kit)

```bash
export CSPULSE_SSH_KEY_FILE=~/.ssh/cspulse-v6-key.pem
export CSPULSE_EC2_HOST=ec2-user@3.94.106.197
./scripts/sync_ec2_runtime_kit.sh
```

Ensures docs + explorer scripts are on EC2 and whitelisted in the platform image on next build.
