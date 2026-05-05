# CS Pulse Platform: High Availability, Scaling & Robustness Plan

**Date**: March 22, 2026
**Status**: Planning
**Target**: Production-grade HA with 99.9% uptime (8.76 hours downtime/year max)

---

## 1. Executive Summary

CS Pulse currently runs as a **single-container monolith** on one EC2 instance. Every component -- Flask API, two MCP servers, nginx, and the event system -- shares a single Docker container with a single PostgreSQL container alongside it. There is no redundancy at any layer.

**Single Points of Failure (SPOFs) identified**: 7
**Crash risks identified**: 9
**Bottlenecks identified**: 6

The platform cannot survive the loss of its single EC2 instance, a gunicorn worker OOM, an MCP server crash, or a PostgreSQL hiccup without user-visible downtime. This document provides a phased plan from "fix it on one server" through "production-grade HA on AWS."

---

## 2. Current Architecture Audit

### 2.1 ASCII Architecture Diagram

```
                        +-----------+
                        | CloudFront|
                        |  (CDN/SSL)|
                        +-----+-----+
                              |
                              | HTTPS :443
                              v
              +-------------------------------+
              |       EC2 Instance (1x)       |
              |   docker-compose.cspulse.yml  |
              |                               |
              |  +-------------------------+  |
              |  |  cspulse-platform       |  |
              |  |  container              |  |
              |  |                         |  |
              |  |  +-------------------+  |  |
              |  |  |    nginx :80      |  |  |
              |  |  |  (daemon on)      |  |  |
              |  |  +--+------+------+--+  |  |
              |  |     |      |      |     |  |
              |  |     |/     |/api  |/mcp |  |
              |  |     |      |      |     |  |
              |  |  +--v-+ +--v---+  |     |  |
              |  |  |React| |Guni-|  |     |  |
              |  |  |HTML | |corn |  |     |  |
              |  |  |files| |:5059|  |     |  |
              |  |  +-----+ |4 wkr|  |     |  |
              |  |           |120s |  |     |  |
              |  |           +-----+  |     |  |
              |  |                    |     |  |
              |  |  /mcp :8001       /mcp/partner :8002
              |  |  +------------+  +------------+  |
              |  |  |MCP Server  |  |Partner MCP |  |
              |  |  |(python3 &) |  |(python3 &) |  |
              |  |  |FastMCP HTTP|  |FastMCP HTTP|  |
              |  |  +------------+  +------------+  |
              |  |                         |  |
              |  |  +-------------------+  |  |
              |  |  | event_system.py   |  |
              |  |  | (in-process       |  |
              |  |  |  daemon threads)  |  |
              |  |  +-------------------+  |  |
              |  +-------------------------+  |
              |                               |
              |  +-------------------------+  |
              |  |  cspulse-postgres       |  |
              |  |  PostgreSQL 16          |  |
              |  |  :5432                  |  |
              |  |  pgdata volume          |  |
              |  +-------------------------+  |
              +-------------------------------+
```

### 2.2 Single Points of Failure (SPOFs)

| # | SPOF | Impact | Evidence |
|---|------|--------|----------|
| 1 | **Single EC2 instance** | Total platform outage | `docker-compose.cspulse.yml` -- one `cs-pulse` service, one `postgres` service, no replicas |
| 2 | **Single PostgreSQL container** | Total data loss risk, total outage | `postgres` service with `pgdata` Docker volume on local disk -- no replication, no Multi-AZ |
| 3 | **MCP Server (port 8001)** | All Claude.ai/MCP integrations fail | `docker-entrypoint.sh:44` -- `python3 mcp_server/cs_pulse_mcp_server.py http) &` -- bare background process, no supervision |
| 4 | **Partner MCP Server (port 8002)** | All partner portal integrations fail | `docker-entrypoint.sh:47` -- same bare `&` pattern |
| 5 | **nginx (in-container)** | All HTTP traffic fails (API + frontend + MCP proxy) | `docker-entrypoint.sh:52` -- `nginx -g "daemon on;"` -- no supervision, no restart-on-crash |
| 6 | **Gunicorn master process** | All API requests fail | `docker-entrypoint.sh:57-64` -- `exec gunicorn` is PID 1, so container dies if master dies |
| 7 | **Docker volume for pgdata** | Data loss on instance termination (EBS-backed mitigates, but no backup automation) | `volumes: pgdata: driver: local` |

### 2.3 Bottlenecks

| # | Bottleneck | Detail |
|---|-----------|--------|
| 1 | **4 gunicorn workers** | All API + webhook + upload traffic shares 4 sync workers. An LLM call (OpenAI/Anthropic) blocks a worker for 10-60s. 4 concurrent LLM calls = API fully blocked. (`GUNICORN_WORKERS=4`, `GUNICORN_TIMEOUT=120`) |
| 2 | **SQLAlchemy default connection pool** | No `pool_size`, `max_overflow`, or `pool_recycle` configured anywhere in `config.py` or `app_v3_minimal.py`. SQLAlchemy defaults to pool_size=5, max_overflow=10. MCP servers create their own Flask app with a separate pool (`cs_pulse_mcp_server.py:106-113`), so total connections = gunicorn_pool + MCP_pool + partner_MCP_pool = potentially 45 connections. |
| 3 | **Synchronous LLM calls** | `agents/signal_analyst_api.py` calls OpenAI synchronously, blocking a gunicorn worker. No async, no task queue. |
| 4 | **In-memory rate limiter** | `RATELIMIT_STORAGE_URL = 'memory://'` in `config.py:131` -- each gunicorn worker has its own counter. Effective rate limit = N * configured_limit. |
| 5 | **Single nginx upstream** | nginx proxies to `127.0.0.1:5059` (gunicorn) and `127.0.0.1:8001/8002` (MCP). No upstream health checks, no failover. |
| 6 | **File-based customer data** | Customer verticals stored at `/app/backend/verticals/customer{id}-{vertical}/` on local disk. `verticals_data` volume mounted for persistence, but not shared across instances. |

### 2.4 Crash Risks

| # | Risk | Detail |
|---|------|--------|
| 1 | **MCP server crash = silent failure** | Started with `&`, no PID tracking, no health check, no restart. If MCP server crashes, nginx returns 502 on `/mcp` forever until container restart. |
| 2 | **OOM on LLM + data processing** | `pandas`, `scikit-learn`, and `numpy` loaded in-process. Large CSV uploads + LLM context building in the same worker can exhaust memory. No `--max-requests` on gunicorn to recycle workers. |
| 3 | **Event system daemon threads** | `event_system.py` uses `threading.Thread(daemon=True)` for event processing and ingestion workers. If the main process crashes or gunicorn forks, these threads are not recoverable. Thread exceptions are silently swallowed. |
| 4 | **Unhandled DB transaction state** | `app_v3_minimal.py:590-593` shows explicit `db.session.rollback()` in login to handle prior aborted transactions. This is a symptom -- other endpoints may hit `InvalidRequestError` if a prior request left a broken transaction. |
| 5 | **Migration failure on startup** | `docker-entrypoint.sh:10` -- `flask db upgrade 2>/dev/null || echo "Note: Migrations skipped"` -- migration failures are silently swallowed. The app may start with an incompatible schema. |
| 6 | **No gunicorn worker recycling** | No `--max-requests` or `--max-requests-jitter` set. Long-running workers accumulate memory from pandas DataFrames, cached KPI catalogs, and SQLAlchemy identity maps. |
| 7 | **Secret key in compose file** | `SECRET_KEY: ${SECRET_KEY:-cspulse-dev-secret-key-min-32-chars}` in `docker-compose.cspulse.yml:66` -- fallback secret key is deterministic. |
| 8 | **DB password in compose file** | `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-cspulse_dev}` -- default password is `cspulse_dev`, same hardcoded in Postgres Dockerfile. |
| 9 | **Health check only checks Flask** | `HEALTHCHECK` in Dockerfile hits `/api/health` on port 5059. Does not verify nginx, MCP servers, or PostgreSQL connectivity. A crashed MCP server or stale DB connection passes the health check. |

---

## 3. Robustness Issues (Fix Before Scaling)

These must be fixed even on a single server. They are independent of horizontal scaling.

### 3a. MCP Server Crash Recovery

**Current state**: `docker-entrypoint.sh` lines 42-48:
```bash
(cd /app/backend && python3 mcp_server/cs_pulse_mcp_server.py http) &
(cd /app/backend && python3 mcp_server/partner_mcp_server.py http) &
```
No PID capture, no monitoring, no restart.

**Fix**: Install `supervisord` in the container and manage all long-running processes:

```ini
# /etc/supervisor/conf.d/cspulse.conf
[program:gunicorn]
command=gunicorn --bind 0.0.0.0:5059 --workers 4 --timeout 120 --max-requests 1000 --max-requests-jitter 50 --access-logfile - --error-logfile - app_v3_minimal:app
directory=/app/backend
autorestart=true
startretries=3
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0

[program:mcp-server]
command=python3 mcp_server/cs_pulse_mcp_server.py http
directory=/app/backend
autorestart=true
startretries=5
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0

[program:partner-mcp]
command=python3 mcp_server/partner_mcp_server.py http
directory=/app/backend
autorestart=true
startretries=5
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0

[program:nginx]
command=nginx -g "daemon off;"
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
```

Replace `docker-entrypoint.sh` with: `exec supervisord -c /etc/supervisor/supervisord.conf`

**Effort**: 2-4 hours
**Impact**: Eliminates SPOFs #3, #4, #5

### 3b. Gunicorn Worker Crash Handling

**Current state**: `exec gunicorn` with 4 workers, 120s timeout. No `--max-requests` to recycle workers, no `--preload` for shared memory.

**Fix**:
```bash
exec gunicorn \
    --bind 0.0.0.0:5059 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "app_v3_minimal:app"
```

- `--max-requests 1000` recycles workers after 1000 requests (prevents memory leaks)
- `--max-requests-jitter 50` prevents all workers recycling simultaneously
- `--graceful-timeout 30` gives in-flight requests 30s to complete during recycling

**Effort**: 30 minutes
**Impact**: Prevents OOM from long-running workers

### 3c. DB Connection Pool Exhaustion

**Current state**: No explicit pool configuration. SQLAlchemy defaults: `pool_size=5`, `max_overflow=10` per app instance. Three separate Flask apps create three pools:
- Gunicorn (4 workers x 15 connections = 60 potential)
- MCP server (1 process x 15 connections = 15)
- Partner MCP (1 process x 15 connections = 15)
- Total potential: 90 connections against a PostgreSQL 16 default of 100 `max_connections`

**Fix**: Add explicit pool config in `config.py`:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 3,
    'max_overflow': 5,
    'pool_recycle': 1800,   # recycle connections every 30 min
    'pool_pre_ping': True,  # test connections before use
    'pool_timeout': 10,     # fail fast if pool exhausted
}
```

Also set pool config in `cs_pulse_mcp_server.py:_get_flask_app()`:
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 2,
    'max_overflow': 3,
    'pool_recycle': 1800,
    'pool_pre_ping': True,
}
```

**Effort**: 1 hour
**Impact**: Prevents connection exhaustion under concurrent load

### 3d. Memory Leaks

**Sources identified**:
1. **No gunicorn worker recycling** -- pandas DataFrames, sklearn models, SQLAlchemy identity maps accumulate
2. **Event system daemon threads** (`event_system.py:79-80`) -- `PriorityQueue` may grow unbounded if consumers are slow
3. **`Event._counter`** (`event_system.py:56`) -- class-level counter increments forever (minor, int is unbounded in Python)
4. **MCP server Flask app** (`_flask_app` global in `cs_pulse_mcp_server.py:88`) -- singleton, but never cleaned up
5. **KPI catalog caching** -- loaded once per process, never invalidated

**Fix**:
- Add `--max-requests 1000` to gunicorn (see 3b)
- Add queue size limits to event system: `queue.PriorityQueue(maxsize=10000)`
- Add periodic `db.session.remove()` in long-running MCP processes
- Monitor RSS per process with `resource.getrusage()` logging

**Effort**: 2-3 hours

### 3e. Synchronous LLM Calls Blocking Workers

**Current state**: `agents/signal_analyst_api.py` calls OpenAI synchronously. A single analysis call can take 10-60 seconds, blocking one of 4 gunicorn workers. Four simultaneous RAG queries = complete API unavailability.

**Fix (immediate, single-server)**:
1. Increase workers to 8 (`GUNICORN_WORKERS=8`) -- more headroom for blocking calls
2. Add a dedicated `/api/rag-query` timeout of 60s (already limited by gunicorn's 120s)
3. Return 202 Accepted + polling endpoint for long-running analyses

**Fix (proper, Phase 2)**:
- Move LLM calls to Celery workers (see Section 4d)
- API returns task_id immediately, client polls for result

**Effort**: 4 hours (immediate) / 2-3 days (Celery)

### 3f. File System Dependencies

**Current state**: Customer data directories at `/app/backend/verticals/customer{id}-{vertical}/` on local disk. Docker volume `verticals_data` is a local volume. Journey files, CSVs, bootstrap configs all stored on filesystem.

**Risks**:
- Cannot scale horizontally (each instance has different files)
- Docker volume loss = customer data loss
- No backup automation

**Fix (Phase 1)**: Automated backup of Docker volumes to S3 via cron
**Fix (Phase 2)**: Migrate file storage to S3 with local cache (see Section 4a)

**Effort**: 2 hours (backup) / 1-2 days (S3 migration)

### 3g. Session Management

**Current state**: Flask-Session configured with `SESSION_TYPE = 'sqlalchemy'` (`config.py:68`), stored in `sessions` table in PostgreSQL. This is already database-backed, so sessions survive across gunicorn workers correctly.

**Status**: Adequately handled for single-server. For multi-server, migrate to Redis for lower latency (see Section 4a).

### 3h. Error Handling

**Current state**: Several patterns indicate fragile error handling:
- `docker-entrypoint.sh` swallows migration errors: `2>/dev/null || echo "Note: Migrations skipped"`
- Login endpoint has explicit `db.session.rollback()` as a workaround for stale transactions
- Many `try/except ImportError` blocks with silent fallbacks (e.g., `activity_logging.py`, `flask_limiter`)
- Event system threads swallow exceptions

**Fix**:
1. Fail-fast on migration errors in production: remove `2>/dev/null`, exit 1 on failure
2. Add `@app.teardown_appcontext` to ensure `db.session.remove()` after every request
3. Add global exception handler: `@app.errorhandler(Exception)` returning structured 500 JSON
4. Add `try/except` with logging in event system thread loops

**Effort**: 3-4 hours

### 3i. Logging

**Current state**: `utils/logging_config.py` has structured logging setup with optional `structlog`. Log files written to `logs/` directory inside container. Gunicorn logs to stdout/stderr. nginx logs to `/var/log/nginx/access.log` with timing format.

**Issues**:
- Log files inside container are lost on container restart
- No log rotation configured for application logs
- No centralized log collection
- nginx and gunicorn logs are separate streams

**Fix (Phase 1)**:
1. Route all logs to stdout/stderr (Docker captures these)
2. Add `RotatingFileHandler` backup with 10MB rotation, 5 backups
3. Add request_id to all log entries for traceability

**Fix (Phase 2)**:
- CloudWatch Logs agent or Fluent Bit sidecar for centralized collection

**Effort**: 2-3 hours (Phase 1) / 1 day (Phase 2)

---

## 4. Horizontal Scaling Strategy

### 4a. Stateless Application Tier

**Goal**: Any request can be served by any instance.

**Step 1 -- Sessions (already OK)**: Sessions use PostgreSQL (`SESSION_TYPE = 'sqlalchemy'`). For better performance under load, migrate to Redis:
```python
SESSION_TYPE = 'redis'
SESSION_REDIS = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
```

**Step 2 -- File storage to S3**:
- Customer verticals: `s3://cspulse-data/verticals/customer{id}-{vertical}/`
- CSV uploads: `s3://cspulse-data/uploads/`
- Journey configs: `s3://cspulse-data/journey-config/`
- Add `boto3` to requirements, create `utils/storage.py` abstraction layer
- Local disk becomes a read-through cache with TTL

**Step 3 -- Rate limiter storage**:
```python
RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/1')
```
Currently `memory://` which is per-worker (see `config.py:131`).

### 4b. Database Scaling

**Read replicas**: MCP servers and dashboard API are read-heavy. Route reads to replica:
```python
SQLALCHEMY_BINDS = {
    'readonly': os.getenv('DATABASE_READONLY_URL'),
}
```

**Connection pooling**: Add PgBouncer as a sidecar (transaction mode):
```yaml
pgbouncer:
  image: edoburu/pgbouncer
  environment:
    DATABASE_URL: postgresql://cspulse:xxx@postgres:5432/cs_pulse
    POOL_MODE: transaction
    MAX_DB_CONNECTIONS: 50
    DEFAULT_POOL_SIZE: 20
```

**Query optimization priorities**:
1. Health score calculations (N+1 query pattern in `calculate_kpi_health`)
2. Context graph traversal (`get_causal_chain` recursive queries)
3. Portfolio-level aggregations (cross-account health rollups)
4. Add indexes on: `(customer_id, account_id)` composite, `health_scores.measured_at`, `context_nodes.account_id`

### 4c. Caching Layer

**Redis caching targets** (ordered by impact):

| Cache Target | TTL | Key Pattern | Invalidation |
|-------------|-----|-------------|--------------|
| Health scores (per account) | 5 min | `health:{customer_id}:{account_id}` | On KPI upload |
| KPI catalog | 1 hour | `kpi_catalog:{vertical}` | On config change |
| MCP platform instructions | 24 hours | `mcp:instructions` | On deploy |
| Account list (per customer) | 5 min | `accounts:{customer_id}` | On account CRUD |
| Portfolio comparison | 15 min | `portfolio:{portfolio_id}` | On health recalc |
| At-risk accounts | 5 min | `at_risk:{customer_id}:{threshold}` | On health recalc |
| Context graph summaries | 15 min | `graph_summary:{customer_id}:{account_id}` | On signal ingest |

**Implementation**:
```python
# utils/cache.py
import redis
import json

_redis = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

def cache_get(key):
    val = _redis.get(key)
    return json.loads(val) if val else None

def cache_set(key, value, ttl=300):
    _redis.setex(key, ttl, json.dumps(value, default=str))

def cache_invalidate(pattern):
    for key in _redis.scan_iter(match=pattern):
        _redis.delete(key)
```

### 4d. Async Processing

**Celery + Redis (or SQS) task queue** for:

| Task | Current | Target |
|------|---------|--------|
| LLM/RAG calls | Sync in gunicorn worker | Celery task, API returns 202 + task_id |
| Data processing (`process_data`) | Sync, blocks MCP for minutes | Celery task |
| Wizard runs (A/B/C) | Sync MCP tool call | Celery task |
| Report generation | Sync | Celery task |
| Health score recalculation | Sync per-account | Celery task batch |
| Event system pub/sub | In-process daemon threads | Redis Pub/Sub or SQS |

**Architecture**:
```
API request -> enqueue task -> return 202 + task_id
                    |
                    v
              Redis (broker)
                    |
                    v
            Celery Worker(s)
                    |
                    v
              Redis (result backend) <- poll via GET /api/tasks/{task_id}
```

**Celery config**:
```python
# celery_app.py
from celery import Celery
celery = Celery('cspulse',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/2'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/3'))
celery.conf.task_soft_time_limit = 120
celery.conf.task_time_limit = 300
celery.conf.worker_max_tasks_per_child = 100  # memory leak protection
```

---

## 5. Kubernetes Migration Plan

### 5a. Container Decomposition

Current monolith splits into 5 independently scalable services:

```
+-------------------------------------------------------+
|                   Kubernetes Cluster                    |
|                                                         |
|  +-------------------+  +-------------------+           |
|  | Ingress Controller|  | cert-manager      |           |
|  | (nginx/ALB)       |  | (Let's Encrypt)   |           |
|  +---------+---------+  +-------------------+           |
|            |                                            |
|    +-------+-------+-------+-------+                    |
|    |       |       |       |       |                    |
|  +-v-+   +-v-+   +-v-+   +-v-+   +-v-+                 |
|  |API|   |MCP|   |MCP|   |Cel|   |Cel|                  |
|  |   |   |Int|   |Par|   |Wkr|   |Wkr|                  |
|  |x3 |   |x2 |   |x1 |   |x2 |   |x1 |                 |
|  +---+   +---+   +---+   +---+   +---+                  |
|    |       |       |       |       |                    |
|    +---+---+---+---+---+---+---+---+                    |
|        |           |           |                        |
|   +----v----+ +----v----+ +----v----+                   |
|   |PostgreSQL| |  Redis  | |   S3    |                  |
|   |RDS Multi-| | Elasti- | | (file   |                  |
|   |AZ        | | Cache   | | store)  |                  |
|   +----------+ +---------+ +---------+                  |
+--------------------------------------------------------+
```

| Service | Replicas | HPA Metric | Min/Max |
|---------|----------|-----------|---------|
| `cspulse-api` | 2-6 | CPU 70% / request latency P95 | 2/6 |
| `cspulse-mcp` | 1-3 | CPU 70% / active connections | 1/3 |
| `cspulse-mcp-partner` | 1-2 | CPU 70% | 1/2 |
| `cspulse-celery-worker` | 1-4 | Queue depth | 1/4 |
| `cspulse-celery-beat` | 1 (singleton) | N/A | 1/1 |

### 5b. Kubernetes Resources

```yaml
# Deployment: cspulse-api
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cspulse-api
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: api
        image: cspulse-api:latest
        ports:
        - containerPort: 5059
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        envFrom:
        - secretRef:
            name: cspulse-secrets
        - configMapRef:
            name: cspulse-config
```

### 5c. Helm Chart Structure

```
charts/cspulse/
  Chart.yaml
  values.yaml
  values-staging.yaml
  values-production.yaml
  templates/
    _helpers.tpl
    deployment-api.yaml
    deployment-mcp.yaml
    deployment-mcp-partner.yaml
    deployment-celery-worker.yaml
    deployment-celery-beat.yaml
    service-api.yaml
    service-mcp.yaml
    ingress.yaml
    hpa-api.yaml
    hpa-mcp.yaml
    configmap.yaml
    secret.yaml
    pdb-api.yaml          # PodDisruptionBudget
    serviceaccount.yaml
```

### 5d. Health Checks

```yaml
# API pod
livenessProbe:
  httpGet:
    path: /api/health
    port: 5059
  initialDelaySeconds: 30
  periodSeconds: 15
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/health
    port: 5059
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 2

startupProbe:
  httpGet:
    path: /api/health
    port: 5059
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 12   # 60s max startup
```

**Enhanced health check** (implement in `app_v3_minimal.py`):
```python
@app.route('/api/health', methods=['GET'])
def health_check():
    checks = {}
    # DB connectivity
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'

    # Redis connectivity (when added)
    # try:
    #     redis_client.ping()
    #     checks['redis'] = 'ok'
    # except: checks['redis'] = 'error'

    status = 'healthy' if all(v == 'ok' for v in checks.values()) else 'degraded'
    code = 200 if status == 'healthy' else 503
    return jsonify({'status': status, 'checks': checks, ...}), code
```

### 5e. Resource Limits

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|------------|-----------|----------------|-------------|
| API | 250m | 1000m | 512Mi | 1Gi |
| MCP Server | 250m | 1000m | 512Mi | 1Gi |
| MCP Partner | 100m | 500m | 256Mi | 512Mi |
| Celery Worker | 500m | 2000m | 1Gi | 2Gi |
| Celery Beat | 50m | 200m | 128Mi | 256Mi |

### 5f. Rolling Update Strategy

- `maxSurge: 1` -- add one new pod before removing old
- `maxUnavailable: 0` -- never reduce below desired count during update
- PodDisruptionBudget: `minAvailable: 1` for API, MCP
- Graceful shutdown: gunicorn `--graceful-timeout 30` + K8s `terminationGracePeriodSeconds: 45`

---

## 6. Alternative: AWS ECS/Fargate

For a small team (1-3 engineers), ECS/Fargate is simpler than Kubernetes.

### 6.1 ECS Service Architecture

```
ALB (:443)
  |
  +-- Target Group: cspulse-api (:5059)
  |     ECS Service: 2 tasks, Fargate
  |
  +-- Target Group: cspulse-mcp (:8001)
  |     ECS Service: 1-2 tasks, Fargate
  |
  +-- Target Group: cspulse-mcp-partner (:8002)
        ECS Service: 1 task, Fargate

Celery Workers:
  ECS Service: 1-3 tasks, Fargate (no ALB target)
  Auto-scale on SQS queue depth

PostgreSQL: RDS Multi-AZ
Redis: ElastiCache (single node or cluster)
Files: S3
```

### 6.2 Comparison Table

| Dimension | Single EC2 (Current) | ECS/Fargate | EKS (Kubernetes) |
|-----------|---------------------|-------------|-------------------|
| **Complexity** | Low | Medium | High |
| **Team expertise needed** | Docker basics | AWS console/CDK | K8s + Helm + kubectl |
| **Auto-scaling** | None | Built-in (task count) | HPA + cluster autoscaler |
| **Zero-downtime deploy** | No | Yes (rolling) | Yes (rolling) |
| **Cost (base)** | ~$80/mo | ~$300-600/mo | ~$800-1500/mo (EKS + nodes) |
| **HA** | None | Multi-AZ automatic | Multi-AZ (if configured) |
| **Vendor lock-in** | Low | Medium (AWS) | Low (portable) |
| **Time to production** | Current | 2-3 weeks | 4-6 weeks |
| **Maintenance burden** | Server patching | Almost none (Fargate) | Cluster upgrades, node management |

**Recommendation**: Start with ECS/Fargate. Migrate to EKS only if multi-cloud or complex scheduling needs arise.

---

## 7. Database HA

### 7.1 RDS Multi-AZ

```
Primary RDS (us-east-1a)  <--->  Standby RDS (us-east-1b)
     |                              (synchronous replication)
     |
     +--- Read Replica (us-east-1c)
           (async replication, for MCP/API reads)
```

- **Automated failover**: ~60s DNS failover to standby on primary failure
- **Read replica**: Route MCP `list_accounts`, `get_account_health`, `search_signals` to replica
- **Instance type**: `db.t3.medium` (2 vCPU, 4 GB) initially; scale to `db.r6g.large` as needed

### 7.2 PgBouncer (Connection Pooling)

Deploy as ECS sidecar or standalone task:
```
App (N connections) -> PgBouncer (pool=20) -> RDS (max_connections=100)
```

Config:
```ini
[databases]
cs_pulse = host=rds-endpoint port=5432 dbname=cs_pulse

[pgbouncer]
pool_mode = transaction
max_client_conn = 200
default_pool_size = 20
reserve_pool_size = 5
server_idle_timeout = 300
```

### 7.3 Backup Strategy

| Method | RPO | RTO | Cost |
|--------|-----|-----|------|
| RDS automated snapshots (daily) | 24 hours | ~30 min | Included |
| RDS PITR (continuous) | 5 minutes | ~30 min | ~$20/mo for 100GB |
| Manual snapshots (before deploys) | 0 | ~30 min | Included |
| Cross-region snapshot copy | 24 hours | ~1 hour | ~$10/mo |

---

## 8. Monitoring and Observability

### 8.1 Metrics (Layered)

**Layer 1 -- Infrastructure (CloudWatch)**:
- EC2/ECS: CPU, memory, network, disk
- RDS: connections, read/write latency, replica lag, free storage
- ALB: request count, 5xx rate, target response time

**Layer 2 -- Application (Prometheus + Grafana or Datadog)**:
- Request rate by endpoint (P50, P95, P99 latency)
- Error rate by status code
- Gunicorn worker utilization
- DB connection pool usage
- MCP tool call duration and error rate
- Celery queue depth and task duration

**Layer 3 -- Business (Custom dashboard)**:
- Health score calculation latency
- Wizard run duration
- Onboarding completion rate
- MCP session count (Claude.ai connections)

### 8.2 Distributed Tracing (OpenTelemetry)

```python
# Add to app_v3_minimal.py
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

FlaskInstrumentor().instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=db.engine)
RequestsInstrumentor().instrument()  # traces LLM HTTP calls
```

### 8.3 Alerting

| Alert | Condition | Channel | Severity |
|-------|-----------|---------|----------|
| API down | Health check fails 3x | PagerDuty | P1 |
| MCP server down | /mcp returns 502 for 2 min | PagerDuty | P1 |
| Error rate spike | 5xx rate > 5% for 5 min | Slack + PagerDuty | P2 |
| DB connections high | Pool utilization > 80% | Slack | P3 |
| Response time degraded | P95 > 5s for 10 min | Slack | P3 |
| Disk usage high | > 80% on any volume | Slack | P3 |
| RDS replica lag | > 10s for 5 min | Slack | P3 |
| Celery queue backlog | > 100 tasks for 10 min | Slack | P3 |
| Certificate expiry | < 14 days | Slack | P4 |

### 8.4 SLA Dashboard

Track and display:
- Uptime percentage (rolling 30/90 days)
- Mean Time to Recovery (MTTR)
- Mean Time Between Failures (MTBF)
- API availability by endpoint group
- Error budget remaining (if using SLO model)

---

## 9. Cost Analysis

### 9.1 Cost by Phase

| Component | Phase 0 (Current) | Phase 1 (Robust Single) | Phase 2 (HA Multi-Server) | Phase 3 (ECS Production) |
|-----------|-------------------|------------------------|--------------------------|--------------------------|
| **Compute** | t3.medium: $30/mo | t3.large: $60/mo | 2x t3.large: $120/mo | 3 Fargate tasks: $180/mo |
| **Database** | Docker PostgreSQL: $0 | RDS db.t3.micro: $15/mo | RDS Multi-AZ db.t3.medium: $65/mo | RDS Multi-AZ + read replica: $130/mo |
| **Redis** | N/A | ElastiCache t3.micro: $12/mo | ElastiCache t3.small: $25/mo | ElastiCache t3.medium: $50/mo |
| **Load Balancer** | N/A | N/A | ALB: $22/mo | ALB: $22/mo |
| **Storage (S3)** | N/A | S3: $5/mo | S3: $5/mo | S3: $5/mo |
| **CloudFront** | $5/mo | $5/mo | $10/mo | $15/mo |
| **Monitoring** | CloudWatch free tier | CloudWatch: $10/mo | CloudWatch + alarms: $30/mo | Datadog or CW: $50/mo |
| **Logging** | None | CW Logs: $5/mo | CW Logs: $10/mo | CW Logs: $15/mo |
| **Celery Workers** | N/A | N/A | 1 Fargate task: $30/mo | 2 Fargate tasks: $60/mo |
| **Secrets Manager** | N/A | $1/mo | $2/mo | $3/mo |
| **Total** | **~$35-80/mo** | **~$115-175/mo** | **~$320-500/mo** | **~$530-850/mo** |

### 9.2 Break-Even Analysis

| Phase | Monthly Cost | Customers to Justify (at $500/mo ARR each) |
|-------|-------------|---------------------------------------------|
| Phase 0 | $80 | 1 (current demo/dev) |
| Phase 1 | $175 | 1-2 paying customers |
| Phase 2 | $500 | 3-5 paying customers |
| Phase 3 | $850 | 5-10 paying customers |

**Rule of thumb**: Move to next phase when downtime cost per hour exceeds the monthly cost difference. If a customer pays $5K/mo ARR and expects 99.9% uptime, one hour of downtime costs ~$7 in SLA credits but potentially $50K+ in churn risk.

---

## 10. Implementation Roadmap

### Phase 1: Robustness Fixes (Week 1-2)

**Goal**: Eliminate crash risks on single server. No architecture changes.

| Task | Section | Effort | Priority |
|------|---------|--------|----------|
| Install supervisord, manage all processes | 3a | 4h | P0 |
| Add `--max-requests` to gunicorn | 3b | 30m | P0 |
| Configure DB connection pool | 3c | 1h | P0 |
| Fail-fast on migration errors in prod | 3h | 1h | P0 |
| Enhanced health check (DB ping) | 5d | 2h | P1 |
| Global exception handler | 3h | 2h | P1 |
| Structured logging to stdout | 3i | 2h | P1 |
| Move PostgreSQL to RDS | 7.1 | 4h | P1 |
| Remove default secrets from compose | 2.4 | 30m | P1 |
| Add request_id to log entries | 3i | 1h | P2 |

**Deliverable**: Single server that self-heals from process crashes, doesn't leak memory, and fails loudly on real errors.

### Phase 2: Redis, Async Workers, Read Replicas (Week 3-6)

**Goal**: Decouple compute from state. Enable horizontal scaling.

| Task | Section | Effort | Priority |
|------|---------|--------|----------|
| Deploy Redis (ElastiCache) | 4c | 2h | P0 |
| Add caching layer for health scores, KPI catalog | 4c | 1d | P0 |
| Move rate limiter storage to Redis | 4a | 30m | P1 |
| Set up Celery + Redis broker | 4d | 1d | P1 |
| Move LLM calls to Celery tasks | 4d | 2d | P1 |
| Move data processing to Celery | 4d | 1d | P1 |
| Add RDS read replica | 7.1 | 2h | P2 |
| Route MCP reads to replica | 4b | 4h | P2 |
| PgBouncer sidecar | 7.2 | 3h | P2 |
| Migrate file storage to S3 | 4a | 2d | P2 |
| Automated RDS backups + PITR | 7.3 | 1h | P2 |

**Deliverable**: Stateless app tier ready for horizontal scaling. LLM calls no longer block API workers.

### Phase 3: ECS/Fargate Migration (Month 2-3)

**Goal**: Multi-instance HA with zero-downtime deploys.

| Task | Section | Effort | Priority |
|------|---------|--------|----------|
| Split Dockerfile into API, MCP, Celery images | 5a | 1d | P0 |
| Create ECS task definitions | 6.1 | 1d | P0 |
| Configure ALB with target groups | 6.1 | 4h | P0 |
| ECS services with desired count >= 2 | 6.1 | 2h | P0 |
| Auto-scaling policies (CPU + queue depth) | 6.1 | 4h | P1 |
| RDS Multi-AZ upgrade | 7.1 | 1h | P1 |
| CI/CD pipeline (GitHub Actions -> ECR -> ECS) | -- | 1d | P1 |
| Blue/green deployment setup | -- | 4h | P2 |
| Secrets Manager integration | -- | 2h | P2 |
| CloudWatch dashboards and alarms | 8.1 | 1d | P2 |

**Deliverable**: Production HA deployment surviving AZ failures, auto-scaling under load, zero-downtime deploys.

### Phase 4: Observability and SLA (Month 4+)

**Goal**: Meet 99.9% SLA with proof.

| Task | Section | Effort | Priority |
|------|---------|--------|----------|
| OpenTelemetry instrumentation | 8.2 | 1d | P1 |
| Alert routing (PagerDuty + Slack) | 8.3 | 4h | P1 |
| SLA dashboard | 8.4 | 1d | P2 |
| Load testing (k6 or Locust) | -- | 2d | P2 |
| Chaos testing (container kills, AZ failure) | -- | 1d | P3 |
| SOC2 logging requirements | -- | 2d | P3 |
| Evaluate EKS migration (if needed) | 6.2 | -- | P4 |

**Deliverable**: Observable, alertable platform with SLA tracking and incident response runbooks.

---

## Appendix A: Key File References

| File | Role | Location |
|------|------|----------|
| Dockerfile | Multi-stage build (frontend + Cython backend + runtime) | `kpi-dashboard/Dockerfile.cspulse` |
| Docker Compose | Service definitions (cs-pulse + postgres) | `kpi-dashboard/docker-compose.cspulse.yml` |
| Entrypoint | Process startup (nginx, MCP, gunicorn) | `kpi-dashboard/docker-entrypoint.sh` |
| nginx config | Reverse proxy (API, MCP, static) | `kpi-dashboard/nginx-cspulse.conf` |
| Flask app | Application entry point | `kpi-dashboard/backend/app_v3_minimal.py` |
| Config | All environment settings | `kpi-dashboard/backend/config.py` |
| MCP Server | Tool provider for Claude.ai | `kpi-dashboard/backend/mcp_server/cs_pulse_mcp_server.py` |
| Event system | In-process pub/sub with daemon threads | `kpi-dashboard/backend/event_system.py` |
| DB extensions | SQLAlchemy instance | `kpi-dashboard/backend/extensions.py` |
| Requirements | Python dependencies | `kpi-dashboard/backend/requirements-core.txt` |
| Logging config | Structured logging setup | `kpi-dashboard/backend/utils/logging_config.py` |
| Postgres Dockerfile | PostgreSQL 16 with init scripts | `kpi-dashboard/docker/postgres/Dockerfile` |
