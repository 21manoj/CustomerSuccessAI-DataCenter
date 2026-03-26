# Feature Build Results — 2026-03-25

## feature/actions-pipeline-push

---

### What was built

| File | Change | Description |
|------|--------|-------------|
| `backend/models.py` | Added | `Notification` and `PlaybookTask` ORM models at end of file |
| `backend/migrations/add_notification_playbook_task_tables.py` | New | DB migration: CREATE TABLE notifications + playbook_tasks with rollback |
| `backend/notifications_api.py` | New | Flask blueprint with 3 notification endpoints |
| `backend/utils/signal_analyst.py` | Replaced stub | Full LLM-backed health drop analysis (Layer A) |
| `backend/utils/urgent_signal_scanner.py` | Replaced stub | Context graph edge scanner for urgent revenue risk (Layer C) |
| `backend/mcp_server/cs_pulse_onboarding.py` | Modified | Wired Layer A + Layer C trigger hooks at end of `_process_data_impl()` |
| `backend/onboarding_api_v2_config_aware.py` | Modified | Wired Layer C scanner at end of `ingest_context_graph_csvs()` |
| `backend/verticals/dc2_s/api_routes.py` | Modified | `get_csm_daily_actions` now prepends pending `PlaybookTask` rows first |
| `backend/app_v3_minimal.py` | Modified | Registered `notifications_api` blueprint |

---

### DB Models added

**`Notification`** (`notifications` table)
- `id` INTEGER PK
- `customer_id` FK → customers.customer_id (NOT NULL)
- `account_id` FK → accounts.account_id (nullable)
- `type` VARCHAR(50): `signal_insight | playbook_triggered | urgent_alert`
- `priority` VARCHAR(20): `normal | high | critical` (default `normal`)
- `payload` JSONB (default `{}`)
- `created_at` TIMESTAMP (default utcnow)
- `read_at` TIMESTAMP (nullable — NULL means unread)
- Indexes: `(customer_id, read_at)`, `(customer_id, type)`, `(priority, created_at)`

**`PlaybookTask`** (`playbook_tasks` table)
- `id` INTEGER PK
- `customer_id` FK → customers.customer_id (NOT NULL)
- `account_id` FK → accounts.account_id (NOT NULL)
- `playbook_id` VARCHAR(20): e.g. `PB-04`
- `trigger_reason` VARCHAR(200): e.g. `arc_assigned:champion_loss`
- `trigger_source` VARCHAR(50): `wizard_a | health_threshold | manual`
- `assigned_csm` VARCHAR(100)
- `due_date` TIMESTAMP (nullable)
- `status` VARCHAR(20): `pending | active | done | dismissed` (default `pending`)
- `created_at` TIMESTAMP (default utcnow)
- Indexes: `(customer_id, status)`, `(account_id, status)`

---

### API Endpoints added

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notifications/unread` | Returns `{ count, notifications[] }` — unread only, sorted by priority DESC then created_at DESC, limit=20 |
| PUT | `/api/notifications/<id>/read` | Sets `read_at = utcnow()`. Returns `{ success, read_at }` |
| GET | `/api/notifications/` | Paginated list. Supports `?type=urgent_alert&limit=50&offset=0&unread=true` |

All endpoints require session authentication (via `get_current_customer_id()`). Tenant-isolated: each customer sees only their own notifications.

---

### Trigger hooks wired

**In `_process_data_impl()` (`cs_pulse_onboarding.py`, after health scores written):**

1. **Layer A — signal_analyst**: For each account, fetches last 2 `HealthScore` rows. If `health_after - health_before <= -10`, calls `check_and_analyze()`. Wrapped in `try/except` — non-fatal.

2. **Layer C — urgent_signal_scanner**: For each account, calls `scan_for_urgent_signals()`. Scans `ContextEdge` rows with `confidence >= 0.85` pointing to `OUTCOME` nodes with `revenue_impact < -50000`. Urgency formula: `abs(revenue_impact) * confidence / max(days_to_renewal, 1)`. Creates `Notification(type='urgent_alert', priority='critical')` when urgency > 5000. Wrapped in `try/except` — non-fatal.

**In `ingest_context_graph_csvs()` (`onboarding_api_v2_config_aware.py`, after edges committed):**

- Layer C scanner runs per-account immediately after edges are committed. `result['urgent_alerts_created']` is appended to the return dict. Wrapped in `try/except` — non-fatal.

**In `get_csm_daily_actions()` (`verticals/dc2_s/api_routes.py`, before account loop):**

- Queries `PlaybookTask.query.filter_by(customer_id=..., status='pending')` and prepends them to `all_actions` with `priority_index=999.0` (sorts to top) and `source='system_triggered'`. Wrapped in `try/except` — non-fatal.

---

### Tests / Verification

**1. DB migration**
```bash
cd kpi-dashboard/backend
python -m migrations.add_notification_playbook_task_tables
# Expected: ✅ Created table: notifications, ✅ Created table: playbook_tasks
```

**2. Notifications API**
```bash
# Unread count
curl -s -b session.cookie http://localhost:5000/api/notifications/unread | jq '.count'

# Mark as read
curl -s -b session.cookie -X PUT http://localhost:5000/api/notifications/1/read | jq .

# Paginated list with filter
curl -s -b session.cookie "http://localhost:5000/api/notifications/?type=urgent_alert&limit=10" | jq .
```

**3. signal_analyst**
- Requires OpenAI API key configured for the customer (`configure_customer_kpis` or `set_openai_api_key()`).
- After `process_data`, check for notifications: `SELECT * FROM notifications WHERE type='signal_insight' ORDER BY created_at DESC LIMIT 5;`
- Force trigger by inserting two `health_scores` rows for the same account with delta > 10 pts.

**4. urgent_signal_scanner**
- Requires context graph edges with `confidence >= 0.85` pointing to OUTCOME nodes with `revenue_impact < -50000`.
- After `ingest_context_graph_csvs()`, check: `SELECT * FROM notifications WHERE type='urgent_alert' ORDER BY created_at DESC;`
- Verify `urgency_score` in payload: `payload->>'urgency_score'`

**5. get_csm_daily_actions with PlaybookTask**
```bash
# Insert a test task
INSERT INTO playbook_tasks (customer_id, account_id, playbook_id, trigger_reason, trigger_source, status)
VALUES (1, 1, 'PB-04', 'arc_assigned:champion_loss', 'wizard_a', 'pending');

# Then call the actions endpoint — PB-04 task should appear first
curl -s -b session.cookie http://localhost:5000/api/dc2s/daily-actions | jq '.actions[0].source'
# Expected: "system_triggered"
```

---

### Open items / Assumptions

1. **`HealthScore` model** — assumed to have `account_id`, `measurement_month`, `health_score`, `contributing_pillars` columns. The health score write in `_process_data_impl` uses a raw SQL upsert, so the SQLAlchemy model must match the actual table schema. Verify with `\d health_scores` in psql.

2. **OpenAI model** — `signal_analyst` uses `gpt-4o-mini` for cost efficiency. Change to `gpt-4o` in `_call_openai()` for higher quality if budget permits.

3. **Renewal date** — `urgent_signal_scanner` reads `profile_metadata['renewal_date']` or `profile_metadata['contract_renewal_date']`. If neither key exists, scanner defaults to `RENEWAL_WINDOW` (60 days) as denominator, making urgency effectively `abs(revenue_impact) * confidence / 60`. This is intentionally conservative.

4. **Notification blueprint registration** — `notifications_api` is registered via a `try/except` import block in `app_v3_minimal.py`. If the import fails (e.g. in Docker before rebuild), the app still boots.

5. **PlaybookTask creation** — tasks are queued (status='pending') but nothing in this PR automatically creates them from Wizard A arc assignments. The `get_csm_daily_actions` hook will surface any tasks that are manually inserted or created by future Wizard A arc-trigger code.

6. **EC2 deployment** — requires `docker compose build --no-cache` to pick up new model columns and blueprint files.

7. **Migration** — run `add_notification_playbook_task_tables.py` BEFORE starting the new container, or add it to the Docker entrypoint migration sequence.
