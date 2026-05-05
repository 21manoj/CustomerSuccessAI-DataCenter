# Flask Hot-Reload & Zero-Downtime Deploy Audit Plan

**Platform**: CS Pulse (Data Center / SaaS Premium verticals)
**Date**: 2026-03-22
**Status**: Planning

---

## 1. Executive Summary

### Why This Matters

CS Pulse runs as a Flask app behind Gunicorn with 4 pre-forked workers, two standalone MCP servers (ports 8001/8002), and Nginx, all inside a single Docker container. Today, **any configuration change** -- health thresholds, KPI weights, system prompts -- requires a full container restart or Gunicorn reload. In production (EC2), this means:

- **10-15 seconds of downtime** during container restart
- **Lost in-flight requests** when workers are killed
- **MCP server disconnects** that break Claude.ai/Claude Desktop sessions mid-conversation
- **Manual SSH** to the EC2 instance to edit files or restart services

### Current Pain Points from MVP Development

1. **Config changes require restart**: Updating `health_thresholds.json` or story arc manifests requires a full redeploy, even though the JSON files are already on disk.
2. **No process supervision**: MCP servers are launched with bare `&` (background). If they crash, they stay dead until the next container restart.
3. **Code deploys require full container rebuild**: `docker compose build --no-cache` + `docker compose up -d` is the only deploy mechanism.
4. **Gunicorn workers share nothing**: Each worker independently loads all Python modules at fork time. Module-level caches (vertical registry, KPI definitions, story arcs) are frozen per-worker.
5. **Weight changes propagate inconsistently**: `CustomerConfig` weights are DB-backed but `ScoreCalculator.__init__()` reads them fresh each instantiation -- this is correct. However, `DEFAULT_PILLAR_WEIGHTS` at module level in `score_calculator.py` is frozen at import time.

---

## 2. Full Audit: What Requires Restart Today

### Category A: Python Code Changes (Restart Expected)

These require a Gunicorn reload or container restart. This is normal and expected behavior for a Python application.

| File / Module | What It Does | Load Pattern |
|---|---|---|
| `app_v3_minimal.py` | Flask app factory, 30+ blueprint registrations | Module-level app creation |
| `config.py` | `Config` / `ProductionConfig` / `DevelopmentConfig` classes | Class attributes evaluated at import (`os.getenv` calls) |
| `models.py` | SQLAlchemy ORM models | Class definitions at import |
| `auth_middleware.py` | `init_auth_middleware()` called once at startup | Startup hook |
| `verticals/dc2_s/api_routes.py` | DC2S-specific API endpoints | Blueprint registration at import |
| `verticals/dc2_s/kpi_definitions.py` | `DC2S_PILLARS`, `DC2S_KPIS` dicts (38 KPIs) | Module-level Python dicts |
| `verticals/saas_premium/kpi_definitions.py` | `SAAS_PILLARS`, `SAAS_KPIS` dicts (41 KPIs) | Module-level Python dicts |
| `vertical_config.py` | `BaseVerticalConfig`, `DataCenterConfig` dataclasses | Class definitions at import |
| `outcome_roi_engine.py` | ROI calculation engine | Module-level constants |
| `event_system.py` | `EventPublisher` with in-memory queue + subscribers | `event_manager.start()` at startup (line 133 of app) |
| `agent_tool_registry.py` | `AgentToolRegistry` singleton | `get_tool_registry()` returns cached singleton |
| `mcp_server/cs_pulse_mcp_server.py` | FastMCP server instance | `mcp = FastMCP(...)` at module level |
| `mcp_server/partner_mcp_server.py` | Partner-scoped MCP server | Separate process, module-level init |
| All 30+ blueprint modules (`kpi_api.py`, `download_api.py`, etc.) | API route handlers | Imported and registered at startup |

### Category B: Configuration That SHOULD Be Dynamic (But Currently Requires Restart)

These are data files or DB-cached values that could be reloaded without restarting the application.

| File / Resource | Current Behavior | Restart Required? |
|---|---|---|
| `config/health_thresholds.json` | Loaded once via `_load()` in `utils/health_thresholds.py`; cached in `_cached` module global. `reload()` function exists but is never called automatically. | Yes (unless `reload()` is called) |
| `config/mcp_system_prompt.md` | Loaded once at MCP server startup via `_load_system_prompt()` (line 49 of `cs_pulse_mcp_server.py`); baked into `FastMCP(instructions=...)` constructor | Yes |
| `config/story_arcs/*.json` | Loaded on-demand by `story_arc_loader.py` via `load_arc()`; no module-level cache, reads from disk each call | **No** (already dynamic) |
| `config/csv_schemas.json` | Loaded fresh from disk on each API call (e.g., `cs_pulse_onboarding.py` line 199) | **No** (already dynamic) |
| `utils/vertical_registry.py` | `_pillars_cache` and `_kpis_cache` are module-level dicts; populated on first call, cached forever | Yes |
| `utils/score_calculator.py` line 21 | `DEFAULT_PILLAR_WEIGHTS = get_default_pillar_weights('dc2_s')` evaluated once at import | Yes (but rarely matters -- `ScoreCalculator.__init__` reads DB) |
| `feature_toggles.py` | In-memory `FeatureToggleManager` with hardcoded defaults; DB-backed per-customer toggles in `FeatureToggle` model are read dynamically | Partial (global toggles: yes; per-customer DB toggles: no) |
| `vertical_config.py` | Dataclass-based config; `get_config(customer_id)` merges DB overrides at call time | **No** (DB overrides are dynamic) |
| Event system subscribers | `event_manager.subscribe()` called at startup; subscriber list is in-memory, never refreshed | Yes |
| Agent tool registry | `AgentToolRegistry` singleton populated via `register_all_tools()`; no refresh mechanism | Yes |
| Playbook trigger config | `PlaybookSystemConfig` dataclass in `vertical_config.py`; constants at import | Yes |

### Category C: Data/DB Changes That Correctly Do NOT Require Restart

| Resource | Why It Works |
|---|---|
| `CustomerConfig` table (pillar weights, KPI weights) | `ScoreCalculator.__init__()` queries DB fresh each instantiation |
| `FeatureToggle` DB model (per-customer flags) | Queried per-request by `feature_toggle_api.py` |
| `HealthScore` / `KPIScore` / `PillarScore` tables | Written and read via ORM per-request |
| `Account` / `Customer` / `User` tables | Standard ORM CRUD |
| `ContextNode` / `ContextEdge` tables | Queried per-request by context graph APIs |
| Uploaded CSV files | Processed on upload; data goes to DB |
| `config/csv_schemas.json` | Read from disk on each request |
| `config/story_arcs/*.json` | `load_arc()` reads from disk each call |
| `vertical_config.py` DB overrides | `get_config()` merges DB values at call time |

---

## 3. Category B Deep Dive -- Config Changes That Should Be Dynamic

### 3.1 health_thresholds.json

**Current behavior** (`utils/health_thresholds.py`):
```python
_cached = None

def _load():
    global _cached
    if _cached is None:
        with open(_CONFIG_PATH, 'r') as f:
            _cached = json.load(f)['thresholds']
    return _cached

def reload():
    global _cached
    _cached = None
    return _load()
```

The `reload()` function exists but is only called if someone explicitly invokes it. No API endpoint triggers it. The Settings UI has a `PUT /api/dc2s/config/health-thresholds` endpoint but it writes to the JSON file without calling `reload()` in each Gunicorn worker.

**Problem**: With 4 Gunicorn workers, calling `reload()` in one worker does NOT affect the other 3. Each worker has its own `_cached` variable.

**Proposed fix**:
- Option A: Add a TTL to `_load()` -- check file mtime every 60 seconds, reload if changed.
- Option B: After the Settings API writes the file, have the endpoint also set a DB flag (`config_version` counter). Each worker checks the counter on next request and reloads if stale.
- Option C: Send `SIGHUP` to Gunicorn master after config change (reloads all workers).

### 3.2 KPI Definitions (Vertical Registry Cache)

**Current behavior** (`utils/vertical_registry.py`):
```python
_pillars_cache: Dict[str, Dict] = {}
_kpis_cache: Dict[str, Dict] = {}

def get_pillars(vertical):
    if vertical not in _pillars_cache:
        _pillars_cache[vertical] = _load_pillars(vertical)
    return _pillars_cache[vertical]
```

Once loaded, pillar/KPI definitions are cached forever in each worker's memory. Changing `kpi_definitions.py` requires a full restart.

**Why this matters less than it seems**: KPI definitions are Python code (not config). They change only during development, not at runtime. The real concern is that `DEFAULT_PILLAR_WEIGHTS` in `score_calculator.py` is also frozen, but `ScoreCalculator.__init__()` correctly reads from DB, so this fallback is rarely hit.

**Proposed fix**:
- Add a `clear_cache()` function to `vertical_registry.py`.
- Wire it to the admin flush-cache API (Section 4c).
- For production, KPI definition changes should go through a code deploy (Category A), not hot-reload.

### 3.3 Pillar Weights (ScoreCalculator)

**Current behavior** (`utils/score_calculator.py`):
```python
# Module level -- frozen at import
DEFAULT_PILLAR_WEIGHTS = get_default_pillar_weights('dc2_s')

class ScoreCalculator:
    def __init__(self, customer_id):
        self.config = self._load_config()  # Reads DB fresh

    def _load_config(self):
        config = CustomerConfig.query.filter_by(customer_id=self.customer_id).first()
        pillar_weights = config.dc2s_pillar_weights or {}
        # Falls back to bootstrap file, then kpi_definitions defaults
```

**Assessment**: This is mostly correct. The DB-first approach means weight changes via the `configure_customer_kpis` MCP tool or Wizard C take effect immediately (next score calculation). The frozen `DEFAULT_PILLAR_WEIGHTS` is only used if no `CustomerConfig` exists, which should never happen for properly onboarded customers.

**Proposed fix**: Low priority. Replace `DEFAULT_PILLAR_WEIGHTS` with a function call to avoid the frozen import, but this is cosmetic.

### 3.4 MCP System Prompt

**Current behavior** (`mcp_server/cs_pulse_mcp_server.py`):
```python
_PROMPT_FILE = os.path.join(_backend_dir, 'config', 'mcp_system_prompt.md')

def _load_system_prompt():
    with open(_PROMPT_FILE, 'r') as f:
        return f.read()

mcp = FastMCP("CS Pulse", instructions=_load_system_prompt())
```

The prompt is loaded once and baked into the FastMCP constructor. Changing `mcp_system_prompt.md` requires restarting the MCP server process.

**Proposed fix**:
- FastMCP may not support dynamic instruction updates. If it does, add a periodic reload (every 5 minutes).
- If not, restart the MCP server process independently (see Section 6).
- Since prompt changes are infrequent (weekly at most), this is low priority.

### 3.5 Story Arc Manifests

**Current behavior** (`utils/story_arc_loader.py`):
```python
def load_arc(arc_id):
    arc_path = ARCS_DIR / arc_id
    # Reads from disk each call
```

**Assessment**: Already dynamic. The `VALID_KPI_CODES` set at the top is frozen at import, but this is a validation set derived from `DC2S_KPIS` and rarely changes.

**No action needed.**

### 3.6 Playbook Config

**Current behavior** (`vertical_config.py`):
The `PlaybookSystemConfig` dataclass contains trigger thresholds and auto-approve/reject thresholds. These are Python constants defined in class bodies, frozen at import.

However, `get_config(customer_id)` merges DB-backed overrides from `CustomerConfig`, so customer-specific playbook overrides are already dynamic.

**Proposed fix**: For platform-wide playbook config changes, these require a code deploy. To make them dynamic, store them in a `PlatformConfig` DB table or a JSON file with TTL-based reloading.

### 3.7 Event System Subscribers

**Current behavior** (`event_system.py`):
```python
class EventPublisher:
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
```

Subscribers are registered at startup via `event_manager.subscribe()`. New event types or subscribers cannot be added at runtime.

**Proposed fix**: Low priority. The event system is internal plumbing. New subscribers require new code (Category A). No dynamic registration needed.

### 3.8 Agent Tool Registry

**Current behavior** (`agent_tool_registry.py`):
```python
_singleton = None

def get_tool_registry():
    global _singleton
    if _singleton is None:
        _singleton = AgentToolRegistry()
        register_all_tools(_singleton)
    return _singleton
```

Tools are registered once. New tools require code changes and restart.

**Proposed fix**: Low priority. Same reasoning as event subscribers -- new tools require new code.

---

## 4. Proposed Solutions

### 4a. Config File Watcher (watchdog library)

**Concept**: Use Python's `watchdog` library to monitor `config/` directory for file changes. On change, call the appropriate `reload()` function.

**Pros**: Automatic, no manual intervention.
**Cons**: Adds a dependency; watchdog threads in each Gunicorn worker; Docker volume mounts may not trigger inotify events reliably.

**Files to watch**:
- `config/health_thresholds.json` -> call `health_thresholds.reload()`
- `config/mcp_system_prompt.md` -> requires MCP server restart (separate process)

**Recommendation**: Skip this approach. TTL-based cache invalidation (4b) is simpler and more reliable in containerized environments.

### 4b. DB-Backed Config with Cache TTL

**Concept**: For config values that change at runtime, store them in the database with a `config_version` counter. Each worker checks the version on a TTL (e.g., 60 seconds) and reloads if stale.

**Implementation sketch**:
```python
import time

class CachedConfig:
    def __init__(self, loader_fn, ttl_seconds=60):
        self._loader = loader_fn
        self._ttl = ttl_seconds
        self._value = None
        self._loaded_at = 0

    def get(self):
        now = time.time()
        if self._value is None or (now - self._loaded_at) > self._ttl:
            self._value = self._loader()
            self._loaded_at = now
        return self._value

    def invalidate(self):
        self._value = None
```

**Apply to**:
- `health_thresholds.py`: Wrap `_load()` in `CachedConfig(ttl=60)`
- `vertical_registry.py`: Add TTL to `_pillars_cache` / `_kpis_cache`

**Recommendation**: Implement this as P1. Simple, no external dependencies, works across all Gunicorn workers independently.

### 4c. Admin API to Flush Caches

**Concept**: Add `POST /api/admin/flush-cache` endpoint that clears all in-memory caches.

**What it flushes**:
1. `health_thresholds.reload()` -- clear threshold cache
2. `vertical_registry.clear_cache()` -- clear pillar/KPI caches (new function)
3. Any future TTL-based caches

**Limitation**: In a multi-worker Gunicorn setup, this endpoint hits ONE worker (whichever Gunicorn routes the request to). The other 3 workers are unaffected.

**Workarounds**:
- Call the endpoint 4+ times (hacky, unreliable)
- Use a DB-based version counter (each worker checks on next request)
- Send `SIGHUP` to Gunicorn master (reloads all workers -- but this is a full code reload, not just cache flush)

**Recommendation**: Implement as P2, combined with TTL caching (4b). The API provides an "immediate flush" option; the TTL provides "eventual consistency" across workers.

### 4d. Gunicorn Graceful Reload (HUP Signal)

**Concept**: `kill -HUP <gunicorn_master_pid>` triggers a graceful reload:
1. Master spawns new workers with fresh code/config
2. Old workers finish serving in-flight requests
3. Old workers are terminated after draining

**Zero-downtime guarantee**: Yes, as long as new workers start successfully before old ones terminate.

**How to trigger from inside the container**:
```bash
# Find Gunicorn master PID (it's PID 1 if using exec in entrypoint)
kill -HUP 1
```

**Docker consideration**: With `exec gunicorn ...` in the entrypoint (line 57 of `docker-entrypoint.sh`), Gunicorn IS PID 1. `kill -HUP 1` works.

**Recommendation**: Implement as P0. This is the simplest path to zero-downtime code deploys.

### 4e. Extend Feature Toggle Pattern

**Current state**: `FeatureToggle` DB model + `FeatureToggleManager` already support per-customer feature flags queried per-request. This pattern is proven and works across all workers.

**Extension opportunity**: Move more configuration into the same pattern:
- Health thresholds could be a `PlatformConfig` DB row
- Global feature flags already work this way

**Recommendation**: Use this pattern for any new configuration that needs to be dynamic. Do not migrate existing file-based config unless there is a specific need.

---

## 5. Gunicorn Zero-Downtime Deploy Strategy

### 5.1 HUP Signal Graceful Reload

```bash
# Inside the container
kill -HUP $(cat /tmp/gunicorn.pid)
# Or if Gunicorn is PID 1:
kill -HUP 1
```

**Behavior**:
1. Master process receives SIGHUP
2. Master re-reads the application module (`app_v3_minimal:app`)
3. Master spawns `GUNICORN_WORKERS` (4) new workers
4. New workers begin accepting requests
5. Old workers stop accepting new requests, finish in-flight work
6. Old workers exit after `graceful_timeout` (default 30s)

**Pre-fork vs Lazy Loading**:
- Current setup uses **pre-fork** (Gunicorn default): app is loaded in the master, then forked.
- On HUP, the master re-imports the app module and forks new workers.
- All module-level code (blueprint imports, `DEFAULT_PILLAR_WEIGHTS`, etc.) re-executes in new workers.

**Requirement**: Add `--pid /tmp/gunicorn.pid` to Gunicorn command for reliable PID lookup.

### 5.2 Docker Rolling Update with Health Checks

For full container replacement (new Docker image):

```yaml
# docker-compose.cspulse.yml additions
services:
  cs-pulse:
    deploy:
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first    # Start new container before stopping old
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5059/api/health"]
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3
```

**Sequence**:
1. Build new image: `docker compose build --no-cache cs-pulse`
2. Rolling update: `docker compose up -d --no-deps cs-pulse`
3. Docker starts new container, waits for health check to pass
4. Docker stops old container

**Caveat**: Docker Compose does not natively support `start-first` ordering (that is Docker Swarm). For plain Compose, use manual blue-green (below).

### 5.3 Blue-Green Deployment

For true zero-downtime with Docker Compose (no Swarm):

1. Run two services: `cs-pulse-blue` and `cs-pulse-green`
2. Nginx upstream points to the active one
3. Deploy to inactive, verify health, switch Nginx upstream, stop old

This is overkill for current scale (single EC2 instance) but documented for future reference.

### 5.4 Recommended Entrypoint Changes

Update `docker-entrypoint.sh`:

```bash
# Add PID file for HUP signal support
exec gunicorn \
    --bind 0.0.0.0:5059 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --graceful-timeout 30 \
    --pid /tmp/gunicorn.pid \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "app_v3_minimal:app"
```

---

## 6. MCP Server Restart Strategy

### 6.1 Current State

```bash
# docker-entrypoint.sh lines 42-48
(cd /app/backend && python3 mcp_server/cs_pulse_mcp_server.py http) &
(cd /app/backend && python3 mcp_server/partner_mcp_server.py http) &
```

**Problems**:
- Bare `&` -- no process supervision
- If the MCP server crashes, it stays dead
- No way to restart MCP without restarting the container
- No PID tracking for targeted restart

### 6.2 Independent MCP Restart

MCP servers run on their own ports (8001, 8002) and have no shared state with Gunicorn workers. They can be restarted independently:

```bash
# Kill and restart MCP server
pkill -f "cs_pulse_mcp_server.py"
(cd /app/backend && python3 mcp_server/cs_pulse_mcp_server.py http) &

# Kill and restart Partner MCP server
pkill -f "partner_mcp_server.py"
(cd /app/backend && python3 mcp_server/partner_mcp_server.py http) &
```

**Impact**: Active MCP sessions (Claude.ai, Claude Desktop) will disconnect and need to reconnect. This is acceptable since MCP sessions are stateless (each tool call is independent).

### 6.3 Process Manager Options

**Option A: supervisord (Recommended)**

Add `supervisord.conf`:
```ini
[supervisord]
nodaemon=true

[program:gunicorn]
command=gunicorn --bind 0.0.0.0:5059 --workers 4 --timeout 120 --pid /tmp/gunicorn.pid app_v3_minimal:app
directory=/app/backend
autorestart=true
stdout_logfile=/dev/stdout
stderr_logfile=/dev/stderr

[program:mcp-server]
command=python3 mcp_server/cs_pulse_mcp_server.py http
directory=/app/backend
autorestart=true
environment=FEATURE_MCP_SERVER=true
stdout_logfile=/dev/stdout
stderr_logfile=/dev/stderr

[program:partner-mcp]
command=python3 mcp_server/partner_mcp_server.py http
directory=/app/backend
autorestart=true
environment=FEATURE_MCP_SERVER=true
stdout_logfile=/dev/stdout
stderr_logfile=/dev/stderr

[program:nginx]
command=nginx -g "daemon off;"
autorestart=true
stdout_logfile=/dev/stdout
stderr_logfile=/dev/stderr
```

**Pros**: Auto-restart on crash, `supervisorctl restart mcp-server` for targeted restart, clean log management.
**Cons**: Adds supervisord as a dependency (small, well-understood).

**Option B: s6-overlay**

Lighter alternative to supervisord, designed for Docker containers. More complex setup but lower resource overhead.

**Recommendation**: Use supervisord (Option A). It is widely understood, well-documented, and trivial to add to the Dockerfile.

---

## 7. Admin Configuration Guide

### 7.1 Change Health Thresholds Without Restart

**Today (requires workaround)**:
1. SSH into EC2: `ssh ec2-user@<host>`
2. Edit the file: `docker compose exec cs-pulse vi /app/backend/config/health_thresholds.json`
3. Restart: `docker compose restart cs-pulse`

**After implementing TTL cache (Section 4b)**:
1. Use the Settings UI (`PUT /api/dc2s/config/health-thresholds`)
2. Wait up to 60 seconds for all workers to pick up the change
3. Or call `POST /api/admin/flush-cache` for immediate effect (one worker)

**After implementing Gunicorn HUP (Section 5.1)**:
1. Use the Settings UI to save new thresholds
2. Send HUP: `docker compose exec cs-pulse kill -HUP 1`
3. All workers reload within 30 seconds

### 7.2 Update KPI Weights Without Restart

**Already works today**:
1. Use the `configure_customer_kpis` MCP tool
2. Or run Wizard C via `trigger_wizard(customer_id, 'c')`
3. Weights are stored in `CustomerConfig` DB table
4. `ScoreCalculator.__init__()` reads from DB on each instantiation
5. No restart needed

### 7.3 Deploy New Code with Zero Downtime

**Current (with downtime)**:
```bash
ssh ec2-user@<host>
cd CustomerSuccessAI-DataCenter
git pull
docker compose -f docker-compose.cspulse.yml build --no-cache
docker compose -f docker-compose.cspulse.yml up -d
# ~30 seconds of downtime
```

**After implementing Gunicorn HUP + supervisord**:
```bash
ssh ec2-user@<host>
cd CustomerSuccessAI-DataCenter
git pull
docker compose -f docker-compose.cspulse.yml build --no-cache
docker compose -f docker-compose.cspulse.yml up -d
# Docker replaces container, supervisord starts all processes
# Health check ensures new container is ready before old one is removed
```

**For Python-only changes (no Docker rebuild needed)**:
```bash
# Copy updated files into running container
docker compose exec cs-pulse cp /host/path/to/file.py /app/backend/file.py
# Graceful reload
docker compose exec cs-pulse kill -HUP 1
```

### 7.4 Restart MCP Servers Without Affecting the Main App

**Today**:
```bash
docker compose exec cs-pulse pkill -f "cs_pulse_mcp_server.py"
docker compose exec cs-pulse bash -c '(cd /app/backend && python3 mcp_server/cs_pulse_mcp_server.py http) &'
```

**After implementing supervisord**:
```bash
docker compose exec cs-pulse supervisorctl restart mcp-server
docker compose exec cs-pulse supervisorctl restart partner-mcp
```

---

## 8. Implementation Priority

### P0: Gunicorn HUP Signal for Zero-Downtime Deploys
**Effort**: 1 hour
**Impact**: Eliminates downtime for code deploys

Changes:
- Add `--pid /tmp/gunicorn.pid` and `--graceful-timeout 30` to Gunicorn command in `docker-entrypoint.sh`
- Document HUP signal procedure
- Add `POST /api/admin/reload` endpoint that sends SIGHUP to Gunicorn master (optional, for UI-triggered deploys)

### P1: Config Cache with TTL (health thresholds, vertical registry)
**Effort**: 2-3 hours
**Impact**: Config changes take effect within 60 seconds without restart

Changes:
- Create `utils/cached_config.py` with `CachedConfig` class (TTL-based)
- Refactor `health_thresholds.py` to use `CachedConfig(ttl=60)`
- Add `clear_cache()` to `vertical_registry.py`
- Add TTL to vertical registry caches (optional -- these rarely change)

### P2: Admin Flush-Cache API
**Effort**: 1-2 hours
**Impact**: Immediate cache invalidation for operators

Changes:
- Create `admin_cache_api.py` blueprint with `POST /api/admin/flush-cache`
- Wire to `health_thresholds.reload()`, `vertical_registry.clear_cache()`
- Add to app blueprint registration in `app_v3_minimal.py`
- Add simple auth check (admin-only)

### P3: Process Manager for MCP Servers (supervisord)
**Effort**: 3-4 hours
**Impact**: Auto-restart on crash, targeted MCP restarts

Changes:
- Add `supervisord` to Dockerfile.cspulse (`pip install supervisor`)
- Create `supervisord.conf` with programs for gunicorn, mcp-server, partner-mcp, nginx
- Update `docker-entrypoint.sh` to exec supervisord instead of manually starting processes
- Test crash recovery: `kill` MCP server, verify auto-restart

### P4: File Watcher for JSON Configs (OPTIONAL)
**Effort**: 3-4 hours
**Impact**: Automatic reload when config files change on disk

Changes:
- Add `watchdog` to requirements
- Create `utils/config_watcher.py` daemon thread
- Watch `config/health_thresholds.json`, `config/story_arcs/*.json`
- Call appropriate reload functions on file change

**Note**: This is optional because TTL-based caching (P1) + admin flush API (P2) cover the same use cases with less complexity. File watchers are unreliable in Docker (inotify does not work with bind mounts on all platforms).

---

## Appendix A: File-by-File Audit Reference

| File | Category | Load Pattern | Dynamic Today? |
|---|---|---|---|
| `app_v3_minimal.py` | A | Module-level app + blueprints | No |
| `config.py` | A | Class attrs from `os.getenv` at import | No |
| `models.py` | A | ORM class definitions | No |
| `config/health_thresholds.json` | B | Cached in `_cached` global; `reload()` exists | Partially (reload exists but not auto-triggered) |
| `config/mcp_system_prompt.md` | B | Loaded once into FastMCP constructor | No |
| `config/csv_schemas.json` | C | Read from disk per-request | Yes |
| `config/story_arcs/*.json` | C | Read from disk via `load_arc()` | Yes |
| `utils/health_thresholds.py` | B | Module-level cache | No (see above) |
| `utils/vertical_registry.py` | B | Module-level cache, no TTL | No |
| `utils/score_calculator.py` | B/C | `DEFAULT_PILLAR_WEIGHTS` frozen; `ScoreCalculator` reads DB | Mostly yes (DB path works) |
| `utils/story_arc_loader.py` | C | Reads disk per-call | Yes |
| `verticals/dc2_s/kpi_definitions.py` | A | Module-level Python dicts | No |
| `verticals/saas_premium/kpi_definitions.py` | A | Module-level Python dicts | No |
| `vertical_config.py` | A/C | Dataclass defaults frozen; DB overrides dynamic | Partially |
| `feature_toggles.py` | B/C | In-memory defaults; DB per-customer flags dynamic | Partially |
| `event_system.py` | A | In-memory pub/sub, started at app init | No |
| `agent_tool_registry.py` | A | Singleton, registered at startup | No |
| `mcp_server/cs_pulse_mcp_server.py` | A | Separate process, module-level init | No |
| `mcp_server/partner_mcp_server.py` | A | Separate process, module-level init | No |
| `docker-entrypoint.sh` | -- | Container entry point | N/A |
| `CustomerConfig` DB table | C | Queried per-request by ScoreCalculator | Yes |
| `FeatureToggle` DB model | C | Queried per-request | Yes |
| `HealthScore` / KPIScore / PillarScore | C | ORM read/write | Yes |

## Appendix B: Gunicorn Config Reference

Current production settings (from `Dockerfile.cspulse` + `docker-entrypoint.sh`):

| Setting | Value | Source |
|---|---|---|
| Workers | 4 | `GUNICORN_WORKERS` env var |
| Timeout | 120s | `GUNICORN_TIMEOUT` env var |
| Bind | `0.0.0.0:5059` | Hardcoded in entrypoint |
| App module | `app_v3_minimal:app` | Hardcoded in entrypoint |
| PID file | None (needs to be added) | -- |
| Graceful timeout | 30s (default) | Not explicitly set |
| Pre-fork | Yes (Gunicorn default) | Not explicitly set |
| Access log | stdout | `--access-logfile -` |
| Error log | stderr | `--error-logfile -` |
