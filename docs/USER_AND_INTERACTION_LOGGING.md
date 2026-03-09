# User and Interaction Logging

This document describes what is currently logged (per user and per interaction) and where.

## Short answer

- **Application log (file):** Every API request and response is logged (method, path, status). For protected routes, the auth middleware also logs user identity (e.g. email) and auth/session details. So in the **log file** you have “every” interaction and, for authenticated requests, the user — but not in a single structured record and not in the database.
- **Database:** Only **specific actions** are written to DB: login (success/failure), logout, settings changes, and RAG queries (separate audit table). You do **not** have every API request or every user action stored in the DB.

So: you have code that logs every request (and user, for protected routes) to the **application logger**, but you do **not** have code that logs every user and every interaction into the **database**.

---

## 1. Request/response logging (every API call) — application log only

**Where:** `kpi-dashboard/backend/app_v3_minimal.py`

- **Before request:** `log_request_info()`  
  - Logs: `API Request: {method} {path}`  
  - No user or customer ID in this line.
- **After request:** `log_response_info()`  
  - Logs: `API Response: {method} {path} -> {status_code}`  

So every API interaction is logged to the app log, but without user/customer in those two lines.

---

## 2. Auth middleware (every protected /api/ request) — application log

**Where:** `kpi-dashboard/backend/auth_middleware.py`

For every request to a protected `/api/` path, the middleware logs at INFO:

- Path, `current_user.is_authenticated`, user type, and (if present) `current_user.email`
- Cookies and session (DEBUG-style; consider reducing in production)

On failure it also logs:

- Unauthorized: path and `request.remote_addr`
- Inactive user: email and path

So in the **log file** you can associate each protected request with a user (e.g. email), but this is not written to the database.

---

## 3. Activity log (database) — specific actions only

**Where:** `kpi-dashboard/backend/activity_logging.py`, model `ActivityLog` (table `activity_logs`)

**What is persisted to DB:**

| Action            | When / where it’s called                          |
|-------------------|----------------------------------------------------|
| Login             | `app_v3_minimal.py` (success and failure)         |
| Logout            | `app_v3_minimal.py` on logout                     |
| Settings change   | `customer_profile_api`, `workflow_config_api`, `openai_key_api` |
| Account update    | `scripts/import_marketplace_accounts.py`          |

**What is not called from app code (methods exist but are unused):**

- `log_upload` / `log_data_upload` (file uploads)
- `log_export` (exports)
- `log_playbook_execution`
- `log_query` (general queries)

So today, **only** login, logout, and the settings/account update flows above are written to `activity_logs`. Other user actions (e.g. uploads, exports, playbook runs, generic queries) are **not** stored in this table.

---

## 4. RAG / query audit (database)

**Where:** `QueryAudit` model and direct RAG API usage

RAG/direct query usage is audited to the database (separate from `ActivityLog`). So “query” interactions for that flow are logged in DB; other API calls are not.

---

## Gaps (if you want “every user and every interaction” in DB)

- No **per-request** audit table that records each API call with user/customer and path/result.
- Uploads, exports, playbook runs, and generic “query” actions are not written to `activity_logs` (helpers exist but are not called).

---

## Recommendation: balance audit value vs performance and DB size

**Goal:** Good security and audit trail without slowing responses or growing the DB unnecessarily.

### 1. Keep request/response in app log only (no change)

- Continue logging every API request and response to the **application log** (method, path, status). Cost is negligible (append to file/stream); you keep full request-level visibility for debugging and forensics.
- **Optional:** Add a single log line that includes `user_id` or `email` when available (e.g. in `after_request`), so you can correlate request logs with users without touching the DB.

### 2. Reduce auth middleware verbosity in production

- In production, **stop** logging cookies and full session on every request (privacy + log size). Keep logging only: path, authenticated yes/no, and user email (or "anonymous"). Reserve full session/cookie dumps for DEBUG or a dedicated security-debug mode.

### 3. DB: only high-value, low-volume events (activity_log + QueryAudit)

- **Do not** add a table that stores every API request. That causes large DB growth and extra write latency for limited day-to-day benefit.
- **Do** use the DB for events that are both meaningful and relatively infrequent:
  - **Keep:** login, logout, settings changes, RAG (QueryAudit) — already in place.
  - **Add calls** where the helpers already exist: `log_upload` on file upload success, `log_export` on export success, `log_playbook_execution` when a playbook run completes. Volume stays low (dozens to hundreds per day per tenant), and you get a clear "who did what" for data and automation.
- Optionally add retention (e.g. archive or drop `activity_logs` and old `QueryAudit` rows after 12–24 months) to cap size.

### 4. If you need more than activity log but less than "every request"

- Only if compliance or policy requires it: log **state-changing** requests to DB (POST/PUT/PATCH/DELETE to important resources), not GETs or health checks. Use a small audit table, background/async write, and retention. That limits bloat and latency while still giving an audit trail for mutations.

**Summary:** Log every request in the **app log**; keep DB for **login, logout, settings, uploads, exports, playbook runs, and RAG**. Reduce auth middleware noise in production and avoid a full per-request DB audit unless you have a concrete requirement for it.

---

## Optional: full request-level audit in DB (only if required)

If compliance or policy explicitly requires **every** request in the database: add an `after_request` hook that writes one row per API call (timestamp, user_id, customer_id, method, path, status_code; no cookies/secrets) via a background queue to avoid latency. Otherwise prefer the balanced approach above.

