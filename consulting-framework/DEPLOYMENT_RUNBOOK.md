# Deployment & Ops Runbook

The ordered procedure an FDE follows to deploy a CS Pulse instance and keep it
running. This is **operational glue, not a module** — it packages the deploy
tooling that already exists in the repo into one runbook. Every command and path
below is real and cited in [Provenance](#provenance); the authoritative in-repo
pattern doc is `docs/DEPLOYMENT_PATTERN_REGISTRY.md`.

> **Do NOT use `kpi-dashboard/EC2_DEPLOYMENT_GUIDE.md` or `ec2-setup.sh`.** Both
> are legacy (old `CustomerSuccessAI-Triad` repo, SQLite, a hardcoded API key) and
> describe a precursor, not the current Postgres stack. They are called out only
> so you skip them. See [Gotcha 6](#gotchas).

## 0. The two deploy paths (pick one)

Both use Docker Compose project name **`cspulse`** and the **same named volumes**
(`cspulse_pgdata`, …), so they are interchangeable against one database.

| Path | Script | Compose | Use when |
|------|--------|---------|----------|
| **A — git-pull + build on EC2** (default for iteration) | `scripts/deploy-ec2-git-pull.sh` | `kpi-dashboard/docker-compose.ec2-build.yml` | day-to-day changes; builds natively on the amd64 host |
| **B — ECR rehydrate** (releases) | `scripts/rehydrate-ec2-ecr.sh` | the 3-file `~/cspulse/` registry stack | shipping a prebuilt image; when you need the `cs-pulse-b` replica |

## 1. Prerequisites

- **AWS CLI** authenticated (the instance role may lack ECR pull, so ECR auth is
  done from your laptop and shipped to the host).
- **SSH key**: `cspulse-v6-key.pem` in the repo root, or point `CSPULSE_SSH_KEY_FILE`
  at it.
- **Target instance**: an EC2 instance tagged `Name=cspulse-v6` (the scripts
  auto-discover it), or pass its id / set `CSPULSE_EC2_INSTANCE_ID`.
- **A populated `.env`** on the host at `~/cspulse/.env` (see §3). First-time
  provisioning is `scripts/provision-ec2-v6.sh` (NOT `ec2-setup.sh`).
- For Path A: `CSPULSE_GITHUB_TOKEN` for the private clone/pull.

## 2. Names & ports (keep this handy — the service/container split trips people)

| Thing | Service name | Container name | Ports |
|-------|-------------|----------------|-------|
| Platform | `cs-pulse` | `cspulse-platform` | 80 (nginx), 443, 5059 (Flask/Gunicorn), 8001 (MCP HTTP), 8002 (partner MCP) |
| Replica (off by default) | `cs-pulse-b` | `cspulse-platform-b` | 9080, 9443, 8002 |
| Postgres | `postgres` | `cspulse-postgres` | `127.0.0.1:5433:5432` (localhost-only) |
| Load driver | `load-driver` | `cspulse-load-driver` | targets `http://cspulse-platform:5059` |

`docker compose … exec cs-pulse …` (service) and `docker exec cspulse-platform …`
(container) hit the **same** container — use whichever the surrounding command
expects. nginx serves: `/` → React, `/api/` → `:5059`, `/mcp` → `:8001` (Bearer
passthrough), `/mcp/<api_key>` → injects `Authorization: Bearer` for trial
customers (`nginx-cspulse.conf`).

## 3. Secrets & the `.env` (read this before touching `.env`)

Runtime config lives in `~/cspulse/.env` (EC2) / `kpi-dashboard/.env` (Path A),
referenced by every compose file.

**Database:** `DATABASE_URL=postgresql://cspulse:${POSTGRES_PASSWORD}@postgres:5432/cs_pulse`
**Secrets (🔒 — never commit these):** `POSTGRES_PASSWORD`, `SECRET_KEY` (≥32 chars),
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `MCP_SERVER_API_KEY`, `MSU_VISION_SECRET_KEY`,
and (Path A build) `ENCRYPTION_KEY`, `QDRANT_API_KEY`, `VOYAGE_API_KEY`.
**Flask:** `FLASK_APP=app_v3_minimal.py`, `FLASK_ENV=production`,
`SESSION_COOKIE_SECURE` (must be `false` on direct-IP HTTP — see Gotcha 2).
**MCP:** `FEATURE_MCP_SERVER=true`, `MCP_SERVER_API_KEY`, `MCP_AUTH_REQUIRED=true`
(production), `MCP_TRANSPORT` (set to `http` by the server's own startup).
**Toggles:** `FEATURE_CONTEXT_GRAPH`, `FEATURE_SIGNAL_ENGINE`, `FEATURE_ASK_AI_V2`
(default true). **Gunicorn:** `GUNICORN_WORKERS` (4), `GUNICORN_TIMEOUT` (120–180).

> **THE CARDINAL `.env` RULE:** never overwrite the whole `~/cspulse/.env`.
> `POSTGRES_PASSWORD` and `SECRET_KEY` were set at first run and Postgres was
> initialized with them — overwriting them causes `password authentication failed
> for user "cspulse"` and a restart loop. To rotate the LLM keys, use the safe
> script (§7), which edits only those keys and backs the file up.

## 4. First-time provisioning (once per instance)

```bash
./scripts/provision-ec2-v6.sh
```

Installs Docker + compose, prepares `~/cspulse/`, and stages the `.env`. (The
legacy `kpi-dashboard/ec2-setup.sh` provisions the *wrong* — SQLite — stack; do
not use it.)

## 5. Deploy

**Path A — git-pull + build (default):**
```bash
CSPULSE_SSH_KEY_FILE=./cspulse-v6-key.pem \
CSPULSE_EC2_INSTANCE_ID=i-xxxxxxxx \
CSPULSE_GITHUB_TOKEN=ghp_xxx \
./scripts/deploy-ec2-git-pull.sh
```
Starts the instance → pulls the repo to `~/CustomerSuccessAI-DataCenter` → **downs
the registry stack keeping volumes** → `docker compose -p cspulse -f
docker-compose.ec2-build.yml build && up -d` → polls `/api/health`.

**Path B — ECR rehydrate (releases):**
```bash
./scripts/rehydrate-ec2-ecr.sh i-xxxxxxxx
# or: CSPULSE_EC2_INSTANCE_ID=i-xxxx ./scripts/rehydrate-ec2-ecr.sh
```
Resolves/starts the instance → SCPs the **3** compose files to `~/cspulse/`
(`docker-compose.ec2-registry.yml`, `docker-compose.ec2-loaddriver.yml`,
`docker-compose.ec2-platform-replica.yml`) → ships an ECR login token → `docker
login` → `pull` + `up -d` across all three. The replica (`cs-pulse-b`) stays off
(it's behind `profiles: ["replica"]`); enable with `--profile replica up -d` only
if the box can take a second full platform.

**Local/dev** (single box, build): `docker compose -f
kpi-dashboard/docker-compose.cspulse.yml up -d --build`.

## 6. What boot does (so you know what "healthy" means)

`docker-entrypoint.sh` runs, in order: seed base verticals into the volume
(`cp -rn`, idempotent) → **schema migrate** (`migrate_schema_sync.py` + named
migrations + `flask db upgrade` + uuid backfill) → start MCP servers on 8001/8002
(if `FEATURE_MCP_SERVER=true`) → `nginx` → `exec gunicorn … app_v3_minimal:app`.
Schema tables are also created by `db.create_all()` at app import — see Module 00
Gotcha 1: `create_all` makes *missing* tables but never ALTERs, which is why the
boot migration step exists.

## 7. Verify

1. **Health:** `curl -f http://<IP>/api/health` → `{status:"healthy", version:"V5",
   server_started_at, uptime_seconds}`. (`server_started_at`/`uptime_seconds` exist
   for stale-process detection — see Troubleshooting.)
2. **Admin first login = magic link.** `POST /api/auth/magic-link`; in dev/no-email
   mode the full magic URL (raw token, **15-min single-use**) prints to stdout —
   read it with `docker logs cspulse-platform`. Verify at
   `/api/auth/verify-magic-link?token=…`.
3. **Smoke the surfaces:** the React app at `http://<IP>/`, `/api/*`, the MCP
   endpoint at `/mcp` (auth-gated), and the persona dashboards.
4. Optional: run the governance auditors as a day-1 baseline —
   `backend/scripts/audit_context_graph.py --customer-id <id>`,
   `scripts/audit_flask_mcp_drift.py`, `tests/test_mcp_tool_auth_coverage.py`.

## 8. Rotate LLM keys (the ONLY safe way to edit `.env`)

```bash
./scripts/update-ec2-api-keys.sh <EC2_IP>     # or CSPULSE_EC2_HOST=…
```
Edits only `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`, timestamp-backs-up `.env`, and
`--force-recreate`s only `cs-pulse`. Never hand-overwrite the whole file (§3).

## 9. Rollback & troubleshooting

- **Rollback:** there is no version-rollback script. Redeploy a prior git ref
  (`deploy-ec2-git-pull.sh --branch <ref>`) or a prior image tag (`PLATFORM_TAG`
  in `.env` + rehydrate). Volumes are preserved by both paths (`down` keeps
  volumes).
- **Stale server (a fix seems to have no effect):** an old gunicorn worker is
  still bound. Detect via the health payload's low `uptime_seconds`/unexpected
  `cwd`; fix with `docker compose … up -d --force-recreate cs-pulse` or a full
  `down`/`up`. Clean worker reload: `kill -HUP $(cat /tmp/gunicorn.pid)`.
- **Confirm a fix actually landed in the running container:**
  `docker exec cspulse-platform grep -n "<marker>" app_v3_minimal.py` (or
  `docker compose … exec cs-pulse grep …`).
- **`password authentication failed for user "cspulse"` / restart loop:** the
  `.env` was clobbered (`POSTGRES_PASSWORD`/`SECRET_KEY` changed). Recovery in
  `docs/EC2_UPDATE_API_KEYS.md:52-58`.
- **Health not passing after deploy:** `docker compose -p cspulse -f
  kpi-dashboard/docker-compose.ec2-build.yml ps` (the git-pull script prints this).
- **Backups:** `scripts/ec2-host-cron-pg-backup-to-s3.sh` (cron pg→S3),
  `scripts/sync-local-db-from-ec2.sh` / `sync-ec2-db-from-local.sh`.

## Gotchas

1. **Postgres name conflict — don't run two stacks at once.** Every compose file
   hardcodes `container_name: cspulse-postgres`. Never `up` the build file
   (`docker-compose.cspulse.yml`/`ec2-build.yml`) *alongside* the registry file —
   the duplicate name conflicts. The git-pull script `down`s the registry stack
   first for exactly this reason.
2. **`SESSION_COOKIE_SECURE` on direct-IP HTTP.** Secure cookies break login over
   `http://<IP>` (no TLS at the origin); the rehydrate script forces
   `SESSION_COOKIE_SECURE=false`. CloudFront still terminates HTTPS at the edge.
   Leave it `true` only when the origin itself is HTTPS.
3. **Service name vs container name** (`cs-pulse` vs `cspulse-platform`) — both
   reach the same container; pick the one the command's context expects (compose
   uses the service, `docker exec`/inter-container DNS uses the container).
4. **The replica is off by default** (`profiles: ["replica"]`) because a second
   full platform is too heavy for a t3 box. Don't assume `cs-pulse-b` is running.
5. **Deprecated/stale artifacts to avoid:** `docker-compose.loaddriver-standalone.yml`
   (deprecated 2026-03-24 — use `load-driver/cs_pulse_driver.py` directly),
   `kpi-dashboard/EC2_DEPLOYMENT_GUIDE.md` + `ec2-setup.sh` (legacy SQLite/Triad),
   `docker-compose.ec2-from-s3.yml` and the `deploy-v*.sh` scripts (precursors).
6. **⚠️ Secret hygiene — a real, open issue in the repo.** A live-looking
   `OPENAI_API_KEY` is hardcoded in `kpi-dashboard/EC2_DEPLOYMENT_GUIDE.md` and
   `kpi-dashboard/ec2-setup.sh`, and load-driver admin credentials are inline in
   `docker-compose.ec2-loaddriver.yml`. **Rotate that key and remove the
   credentials from source before this runbook is shared externally.** Treat the
   exposed key as compromised.

## Provenance

Origin tooling: `docs/DEPLOYMENT_PATTERN_REGISTRY.md` (authoritative pattern);
`scripts/rehydrate-ec2-ecr.sh`, `scripts/deploy-ec2-git-pull.sh` +
`scripts/ec2-git-pull-rebuild.sh`, `scripts/provision-ec2-v6.sh`,
`scripts/update-ec2-api-keys.sh`, `docs/EC2_UPDATE_API_KEYS.md`;
`kpi-dashboard/docker-compose.{ec2-registry,ec2-build,ec2-platform-replica,ec2-worker,cspulse}.yml`,
root `docker-compose.ec2-loaddriver.yml`; `kpi-dashboard/Dockerfile.cspulse`,
`kpi-dashboard/docker-entrypoint.sh`, `kpi-dashboard/nginx-cspulse.conf`;
`kpi-dashboard/backend/app_v3_minimal.py` (health `/api/health`, magic-link,
`db.create_all`); backup scripts `scripts/ec2-host-cron-pg-backup-to-s3.sh`,
`scripts/sync-{ec2-db-from-local,local-db-from-ec2}.sh`. Mapped 2026-08-07 against
HEAD `25397567e`. Deploy-specific behavior (name split, `.env` cardinal rule,
postgres-conflict, cookie-secure) verified against the compose files and the two
deploy scripts directly.
