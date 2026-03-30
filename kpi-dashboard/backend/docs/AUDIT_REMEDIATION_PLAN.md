# Audit Remediation Plan — March 30, 2026

Prioritized plan to fix all gaps found in the UI, Super Admin, and Naming audits.
Organized into 4 sprints (S1-S4) by impact and dependency order.

---

## Sprint 1: Foundation Fixes (P0 — Blocking for Demos/Sales)

### S1.1 — Feature Toggle Admin Panel
**Problem:** 9 of 12 global feature toggles have NO UI control. Admins must use env vars or direct API calls.
**Effort:** 4-6 hours | **Files:** 2 new, 1 modified

**Plan:**
1. Create `src/components/admin/FeatureTogglePanel.tsx`
   - Fetch all toggles via `GET /api/feature-toggle` (already exists)
   - Render toggle switches for all 12 global flags with descriptions
   - Group by category: Core (FORMAT_DETECTION, MULTI_FORMAT_SUPPORT, ENHANCED_UPLOAD), AI (EVENT_DRIVEN_RAG, CONTINUOUS_LEARNING, SIGNAL_ENGINE, ASK_AI_V2), Platform (TEMPORAL_ANALYSIS, REAL_TIME_INGESTION), Revenue (REVENUE_INTELLIGENCE, CONTEXT_GRAPH, MCP_SERVER)
   - Save via `POST /api/feature-toggle` (already exists)
   - Add "requires restart" badge on toggles that need container restart
2. Wire into Super Admin Console (`SuperAdminConsole.tsx`) as a new tab
3. Wire into Settings page (`dc_Settings.tsx`) as a new tab (for customer-scoped toggles)

**Acceptance:** Admin can view and toggle all 12 flags from UI. No env var editing needed.

---

### S1.2 — Role-Gated Dashboard Routes
**Problem:** CSM, VP CS, Ops, and Sales dashboards have no entitlement gates. Any authenticated user can navigate directly to them.
**Effort:** 2-3 hours | **Files:** 2 modified

**Plan:**
1. Create `src/components/shared/EntitlementGuard.tsx` — wrapper component
   - Props: `requiredFeature: string`, `fallback?: ReactNode`
   - Uses `useEntitlements()` hook to check
   - If not entitled: renders upgrade prompt (not blank page)
   - Pattern: `<EntitlementGuard requiredFeature="dashboards"><CRODashboard /></EntitlementGuard>`
2. Update `src/App.tsx` (or route config) to wrap persona dashboard routes:
   - `/cro`, `/cfo` → require `revenue_intelligence`
   - `/csm` → require `dashboards` (Starter+)
   - `/vpcs`, `/ops` → require `dashboards` (Starter+)
   - `/sales` → require `dashboards` (Starter+)
   - `/portco-dashboard` → require `portfolio_synergy` (Enterprise)
3. Add upgrade prompt component: icon + "This dashboard requires [tier]. Contact your admin."

**Acceptance:** Direct URL navigation to restricted dashboards shows upgrade prompt instead of empty/broken page. Backend still enforces via decorators (defense in depth).

---

### S1.3 — Sync Frontend/Backend Entitlement Catalogs
**Problem:** 4 mismatches between frontend `useEntitlements.ts` FEATURE_CATALOG and backend `entitlements.py`.
**Effort:** 1 hour | **Files:** 2 modified

**Plan:**
1. Add to frontend FEATURE_CATALOG: `feedback_loop`, `agent_memory_shared`, `api_key_self_service`
2. Fix `approval_queue` tier: change from `professional` to `enterprise` in frontend
3. Verify `journey_visualizer` — if backend doesn't gate it, remove from frontend catalog (or add backend gate)
4. Reconcile `portfolio_synergy` vs `multi_provider` naming — pick one, update both sides

**Acceptance:** `Object.keys(FRONTEND_CATALOG).sort()` === `Object.keys(BACKEND_CATALOG).sort()`

---

### S1.4 — Remaining Non-Canonical Arc Names in Data
**Problem:** Live customer CSVs in `verticals/customer436-dc2_s/data/` contain non-canonical arc assignments (engagement_decline, champion_loss).
**Effort:** 1-2 hours | **Files:** 0 code changes, operational

**Plan:**
1. Write a one-time migration script (`scripts/migrate_arc_names.py`):
   - Scan all `verticals/customer*` directories for CSV files containing old arc names
   - Map: `champion_loss` → `exec_sponsor_change`, `engagement_decline` → `silent_churn`, `competitor_evaluation` → `competitive_displacement`, `infrastructure_decay` → `stalled_deployment`, `budget_pressure` → `competitive_displacement`, `steady_performer` → `seasonal_surge`
   - Also update `ContextNode` records in DB: `UPDATE context_nodes SET node_subtype = 'exec_sponsor_change' WHERE node_subtype = 'champion_loss'`
2. Run on EC2 against active customers (451, 449, 446)
3. Re-run Wizard A for affected customers to regenerate journey JSONs with canonical names
4. Delete the migration script after running (one-time)

**Acceptance:** `grep -r "champion_loss\|engagement_decline\|competitor_evaluation\|infrastructure_decay\|budget_pressure\|steady_performer" verticals/` returns zero matches.

---

## Sprint 2: Super Admin Escalation Tools (P1 — Required for Production)

### S2.1 — Health Score Reset API + UI
**Problem:** Super admin cannot trigger health score recalculation for a specific account. Only full-customer process_data exists.
**Effort:** 3-4 hours | **Files:** 2 new, 1 modified

**Plan:**
1. Backend: Add `POST /api/admin/accounts/<account_id>/reset-health` to `admin_api.py`
   - Accepts: `{ "dry_run": bool, "reason": string }`
   - Dry run: returns what would change (current score, projected score) without writing
   - Execute: deletes existing HealthScore/PillarScore/KPIScore rows for account, re-runs ScoreCalculator, writes new scores
   - Logs action to activity_log with admin user_id and reason
   - Requires @admin_required decorator
2. Backend: Add `POST /api/admin/customers/<cid>/reset-all-health` — batch version for all accounts
3. Frontend: Add "Recalculate Health" button in SuperAdminConsole customer detail view
   - Shows confirmation dialog with dry-run preview
   - Requires reason text input
   - Shows before/after scores on completion

**Acceptance:** Admin clicks button → sees dry-run preview → confirms → scores recalculated → audit log entry created.

---

### S2.2 — Weight Override API + UI
**Problem:** Super admin cannot directly override Wizard C learned weights. Must edit DB manually.
**Effort:** 3-4 hours | **Files:** 2 new, 1 modified

**Plan:**
1. Backend: Add `POST /api/admin/customers/<cid>/override-weights` to `admin_api.py`
   - Accepts: `{ "pillar_weights": {...}, "kpi_weights": {...}, "reason": string, "source": "admin_override" }`
   - Writes to CustomerConfig.dc2s_pillar_weights / dc2s_kpi_weights
   - Sets a `weight_override_source` field to distinguish admin overrides from Wizard C calibrations
   - Validates weights sum to 1.0 per pillar (reuse existing normalization logic)
   - Logs to activity_log
2. Backend: Add `POST /api/admin/customers/<cid>/reset-weights` — revert to catalog defaults
3. Frontend: Add "Weight Override" panel in SuperAdminConsole customer detail
   - Shows current weights (source: Wizard C / Admin Override / Default)
   - Editable sliders with real-time sum validation
   - "Reset to Defaults" button
   - Requires reason text

**Acceptance:** Admin can override weights, see the source label, and revert to defaults. All changes audited.

---

### S2.3 — Cross-Tenant Activity Audit
**Problem:** Activity logs are customer-scoped. Super admin cannot view logs across all customers or search by user.
**Effort:** 3-4 hours | **Files:** 1 new, 1 modified

**Plan:**
1. Backend: Add `GET /api/admin/activity-logs` to `admin_ui_api.py`
   - Accepts query params: `user_id`, `customer_id` (optional), `action_type`, `date_from`, `date_to`, `limit`, `offset`
   - When `customer_id` is omitted → returns logs across ALL customers (super admin only)
   - Returns: activity entries + customer_name + user_email for context
   - Requires @super_admin_required decorator (stricter than @admin_required)
2. Backend: Add `GET /api/admin/activity-logs/search` — full-text search on action details
3. Frontend: Add "Activity Audit" tab in SuperAdminConsole
   - Filterable table: customer dropdown, user dropdown, action type, date range
   - Search box for full-text search
   - Export to CSV button
   - Color-coded action types (red for destructive, green for creation, yellow for modification)

**Acceptance:** Super admin can search "who deleted customer X's data?" across all tenants in one view.

---

### S2.4 — Approval Queue Override for Admin
**Problem:** Super admin cannot view/manage approval queues across customers, cannot force-execute or override auto-rejected actions.
**Effort:** 3-4 hours | **Files:** 1 new, 2 modified

**Plan:**
1. Backend: Add to `admin_ui_api.py`:
   - `GET /api/admin/approvals/pending` — list all pending approvals across all customers
   - `POST /api/admin/approvals/<id>/force-execute` — override and execute (requires reason)
   - `POST /api/admin/approvals/<id>/force-reject` — override and reject (requires reason)
   - All actions logged with `decided_by = admin_user_id`, `override_reason`
2. Modify `approval_queue.py`:
   - Add `force_execute(request_id, admin_user_id, reason)` method
   - Add `force_reject(request_id, admin_user_id, reason)` method
   - Both bypass confidence thresholds, log override
3. Frontend: Add "Approval Queue" tab in SuperAdminConsole
   - Shows all pending approvals across all customers
   - Grouped by customer
   - Force Execute / Force Reject buttons with reason dialog
   - History view showing all overrides

**Acceptance:** Super admin can see all pending approvals across tenants, force-execute any action with audit trail.

---

## Sprint 3: Admin UX & Monitoring (P2 — Quality of Life)

### S3.1 — Emergency Pause
**Problem:** No way to pause all automated actions for a customer during an incident.
**Effort:** 2-3 hours | **Files:** 2 new, 2 modified

**Plan:**
1. Backend: Add `emergency_paused` boolean to `CustomerConfig` model (default False)
2. Backend: Add endpoints to `admin_ui_api.py`:
   - `POST /api/admin/customers/<cid>/emergency-pause` — sets flag, logs reason
   - `POST /api/admin/customers/<cid>/emergency-resume` — clears flag, logs
3. Modify `approval_queue.py`: Check `emergency_paused` before auto-executing any action
   - If paused: all actions go to PENDING regardless of confidence
   - Add banner text to approval: "Customer is in emergency pause mode"
4. Modify playbook trigger evaluation: skip auto-triggers when paused
5. Frontend: Add red "Emergency Pause" toggle button in SuperAdminConsole customer detail
   - Visual indicator: red banner across customer detail when paused
   - Requires reason text

**Acceptance:** Admin pauses customer → all auto-executions halt → all actions queue for human review → resume restores normal behavior.

---

### S3.2 — Wizard B/C Configuration UI
**Problem:** Wizards B & C have trigger buttons but no configuration or output inspection UI.
**Effort:** 4-5 hours | **Files:** 1 new, 1 modified

**Plan:**
1. Frontend: Enhance `WizardsTab.tsx` in dc_Settings:
   - **Wizard B section:**
     - Show last run date and duration
     - Display discovered patterns as cards (from `GET /api/admin/wizard-b/patterns`)
     - Display early warning rules (from `GET /api/admin/wizard-b/early-warnings`)
     - "View Full Report" button → renders markdown report
   - **Wizard C section:**
     - Show current weights vs catalog defaults (side-by-side comparison table)
     - Show weight history chart (from `GET /api/admin/wizard-c/weights/history`)
     - Show accuracy metrics (from `GET /api/admin/wizard-c/accuracy`)
     - "Approval required" toggle (already backend-supported via Wizard C approval toggle)
     - "Revert to defaults" button → calls reset-weights API from S2.2
     - "Recalibrate" button with confirmation dialog showing what will change

**Acceptance:** User can see Wizard B patterns, Wizard C learned weights vs defaults, and approve/revert changes — all from UI.

---

### S3.3 — Test Runner UX for Stripped Options
**Problem:** When Starter-tier users access Test Runner, advanced options are silently stripped with no explanation.
**Effort:** 1-2 hours | **Files:** 1 modified

**Plan:**
1. Modify `DCTestRunner.tsx`:
   - When options are filtered by `filter_test_runner_options()`, show a subtle info banner:
     "Some advanced scenarios require Professional tier. [Learn more]"
   - Disabled (greyed-out) scenario cards for unavailable scenarios instead of hiding them completely
   - Each disabled card shows lock icon + tier requirement
2. Link "Learn more" to entitlements/upgrade page

**Acceptance:** Starter user sees all scenarios, unavailable ones greyed out with tier badge. No confusion about "missing" features.

---

### S3.4 — Entitlement Rejection Logging
**Problem:** No logging when backend rejects a request due to insufficient entitlements.
**Effort:** 1-2 hours | **Files:** 1 modified

**Plan:**
1. Modify `@require_entitlement` decorator in `auth_decorators.py`:
   - On rejection (403): log to activity_log with action_type='entitlement_rejected'
   - Include: customer_id, user_id, feature_name, endpoint, timestamp
   - Rate-limit logging: max 1 log per (customer_id, feature_name) per 5 minutes to avoid spam
2. Add `GET /api/admin/entitlement-rejections` endpoint for super admin
   - Shows which customers are hitting entitlement walls
   - Useful for sales: "Customer X tried to access Signal Analyst 47 times this week"

**Acceptance:** Sales team can query which features customers are trying to access but can't — drives upgrade conversations.

---

## Sprint 4: Enterprise Features & Polish (P3 — Future)

### S4.1 — Enterprise Feature Management UI
**Problem:** Enterprise features (onboarding_agent, auto_trigger_pipeline, feedback_loop) have zero UI. Backend-only.
**Effort:** 4-6 hours | **Files:** 3 new

**Plan:**
1. Create `src/components/admin/EnterpriseFeatures.tsx`
   - Card-based UI for each enterprise feature
   - Status indicator (enabled/disabled/configured)
   - Configuration panels per feature:
     - **onboarding_agent**: auto-provisioning rules, welcome email templates
     - **auto_trigger_pipeline**: trigger conditions, cooldown periods, excluded accounts
     - **feedback_loop**: feedback collection frequency, sentiment thresholds
2. Backend: Add configuration endpoints if missing (some may need new API routes)
3. Wire into SuperAdminConsole and customer Settings

**Acceptance:** Enterprise customers can configure all 3 features from UI without backend access.

---

### S4.2 — Cross-Tenant Account Search
**Problem:** Super admin cannot search accounts across all customers.
**Effort:** 2-3 hours | **Files:** 1 new, 1 modified

**Plan:**
1. Backend: Add `GET /api/admin/accounts/search` to `admin_ui_api.py`
   - Query params: `q` (name search), `health_min`, `health_max`, `arr_min`, `customer_id` (optional)
   - Returns: account_id, account_name, customer_name, health_score, arr, status
   - Requires @super_admin_required
2. Frontend: Add "Account Search" tab in SuperAdminConsole
   - Search bar + filter chips (health status, ARR range)
   - Results table with click-through to customer detail

**Acceptance:** Admin types "Matterhorn" → sees matching accounts across all customers.

---

### S4.3 — User Impersonation
**Problem:** Super admin cannot reproduce user issues by viewing the platform as that user.
**Effort:** 3-4 hours | **Files:** 2 new, 2 modified

**Plan:**
1. Backend: Add `POST /api/admin/impersonate/<user_id>` to `admin_ui_api.py`
   - Creates a temporary session with target user's customer_id and role
   - Sets `session['impersonating'] = True` and `session['real_admin_id'] = admin_user_id`
   - Logs impersonation start to activity_log
2. Backend: Add `POST /api/admin/stop-impersonation` — restores admin session
3. Frontend: When `session.impersonating === true`:
   - Show persistent yellow banner: "Viewing as [user] at [customer]. [Stop Impersonation]"
   - All actions are read-only (no writes while impersonating)
   - Banner follows user across all pages

**Acceptance:** Admin clicks "View as" → sees exactly what user sees → yellow banner visible → clicks "Stop" → back to admin view. Full audit trail.

---

### S4.4 — Context Graph Sub-Toggle UX
**Problem:** Sub-toggle UI appears disabled with no explanation when Context Graph master toggle is OFF.
**Effort:** 1 hour | **Files:** 1 modified

**Plan:**
1. Modify `ContextGraphSettings.tsx`:
   - When master toggle is OFF: show sub-toggles greyed out with tooltip "Enable Context Graph first"
   - When master toggle is ON: animate sub-toggles becoming available
   - Add descriptive text under each sub-toggle explaining what it does and its dependencies

**Acceptance:** User enables Context Graph master toggle → sub-toggles animate to enabled state with clear descriptions.

---

## Summary Matrix

| ID | Title | Sprint | Priority | Effort | Impact |
|----|-------|--------|----------|--------|--------|
| S1.1 | Feature Toggle Admin Panel | S1 | P0 | 4-6h | High — unblocks admin self-service |
| S1.2 | Role-Gated Dashboard Routes | S1 | P0 | 2-3h | High — security + UX |
| S1.3 | Sync Entitlement Catalogs | S1 | P0 | 1h | Medium — correctness |
| S1.4 | Migrate Non-Canonical Arc Names | S1 | P0 | 1-2h | Medium — data consistency |
| S2.1 | Health Score Reset API + UI | S2 | P1 | 3-4h | High — escalation tool |
| S2.2 | Weight Override API + UI | S2 | P1 | 3-4h | High — escalation tool |
| S2.3 | Cross-Tenant Activity Audit | S2 | P1 | 3-4h | High — compliance + debug |
| S2.4 | Approval Queue Override | S2 | P1 | 3-4h | High — escalation tool |
| S3.1 | Emergency Pause | S3 | P2 | 2-3h | Medium — incident response |
| S3.2 | Wizard B/C Configuration UI | S3 | P2 | 4-5h | Medium — transparency |
| S3.3 | Test Runner UX | S3 | P2 | 1-2h | Low — polish |
| S3.4 | Entitlement Rejection Logging | S3 | P2 | 1-2h | Medium — sales enablement |
| S4.1 | Enterprise Feature Management UI | S4 | P3 | 4-6h | Medium — enterprise tier |
| S4.2 | Cross-Tenant Account Search | S4 | P3 | 2-3h | Medium — admin efficiency |
| S4.3 | User Impersonation | S4 | P3 | 3-4h | Medium — support efficiency |
| S4.4 | Context Graph Sub-Toggle UX | S4 | P3 | 1h | Low — polish |

**Total estimated effort:** 36-50 hours across 4 sprints

**Sprint cadence recommendation:**
- S1 (P0): This week — 8-12 hours
- S2 (P1): Next week — 12-16 hours
- S3 (P2): Week after — 8-12 hours
- S4 (P3): Backlog — 10-14 hours, implement as needed
