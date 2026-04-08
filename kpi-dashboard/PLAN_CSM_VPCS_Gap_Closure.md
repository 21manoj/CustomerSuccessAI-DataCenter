# CSM & VP CS Dashboard — Gap Closure Plan

## Context

Evaluated from Session 3 (Apr 5-6): CSM grade **A-**, VP CS grade **A-**.
Both are close to production-ready. CSM needs real data wiring and notification system. VP CS needs drilldown navigation and health trend loading.

## Current State

### CSM Dashboard (Grade: A-)
**Built:**
- Two layout modes: Focus Flow (Superhuman-inspired sequential queue) and Cockpit (Linear-inspired Kanban)
- Icon rail navigation: Home, Actions, Accounts, Approvals, Renewals
- Daily action queue with urgency-based prioritization (Critical/High/Medium/Opportunity)
- Priority formula: `(impact × 0.6 × arr_weight) - (effort × 0.4)`
- Playbook approval workflow with inline actions
- Active playbook tracker showing in-flight execution status
- Email draft modal, notification bell, AI assistant portal
- Account detail drawer with signals, people, tickets, history tabs
- Backend: `/api/dc2s/daily-actions` fully built — top 10 prioritized actions with ROI context

**Missing:**
- Real playbook execution start (form exists, POST integration incomplete)
- Email send integration (modal only, no backend call)
- Real-time notifications (NotificationBell renders mock data, no WebSocket/polling)
- Search/filtering within views (field rendered but not wired)
- CSM assignment UI (no way to reassign accounts)
- Performance for 100+ accounts (no list virtualization)

### VP CS Dashboard (Grade: A-)
**Built:**
- Dark-themed team performance overview with summary cards (Total Accounts, Avg Health, Playbook Completion %, Renewals 90d)
- Account Health Distribution (Healthy/At-Risk/Critical buckets with ARR)
- CSM Scorecard (accounts managed, health delta, playbook success rate, revenue impact)
- Team Capacity gauge (accounts per CSM vs target, utilization %)
- Renewal Pipeline (90-day window with ARR at risk)
- Portfolio trajectory analysis (improving/declining/stable)
- Backend: `/api/dc2s/csm-scorecard`, `/api/dc2s/team-capacity`, `/api/dc2s/playbook-success-metrics`, `/api/dc2s/health-score-history` all fully built

**Missing:**
- Health Trends view doesn't load real health scores from API
- Drilldown from summary cards → detail pages
- CSM reassignment workflow
- Playbook success rate by lifecycle phase
- Renewal risk prediction (dates shown, churn probability not integrated)
- Team metrics heatmap (nav links exist, view incomplete)
- Export / scheduled report generation

---

## Sprint 1: CSM Data Wiring & Live State (1 week)

### Goal
CSM dashboard shows real data from backend, playbook execution works end-to-end.

### Tasks
1. **Wire daily actions to API** — CSMFocusFlow and CSMCockpit call `/api/dc2s/daily-actions` on mount, respect CSM filter
2. **Playbook execution POST** — PlaybookStartModal submits to `/api/dc2s/playbooks/executions`, receives execution_id, updates tracker
3. **Account list from API** — Accounts view calls `/api/dc2s/accounts` with health classification
4. **Renewal data from API** — Renewals view pulls from account data, sorts by days-to-renewal
5. **Search/filter wiring** — Action queue search filters by account name, playbook type, urgency level
6. **Error states** — All API calls show skeleton loaders during fetch, error boundaries on failure
7. **Mock data removal** — Remove hardcoded mock arrays, replace with API-fetched state

### Acceptance Criteria
- Focus Flow and Cockpit both render real actions from a live backend
- CSM can start a playbook, see it in Active Tracker, complete steps
- Accounts view shows real health scores with correct classification colors

---

## Sprint 2: VP CS Live Data + CSM Notifications (1 week)

### Goal
VP CS dashboard loads all data from APIs. CSM gets basic notification system.

### Tasks

**VP CS:**
1. **Health Trends view** — Wire to `/api/dc2s/health-score-history?months=12`, render trajectory chart
2. **Summary card drilldowns** — Click "At-Risk: 8" → filtered account list showing only at-risk
3. **CSM Scorecard API integration** — Load per-CSM metrics from `/api/dc2s/csm-scorecard`
4. **Team Capacity live data** — Load from `/api/dc2s/team-capacity`, show utilization vs target
5. **Playbook success metrics** — Load from `/api/dc2s/playbook-success-metrics`, show per-playbook ROI table

**CSM Notifications:**
6. **Polling notification system** — 30s poll to `/api/dc2s/daily-actions?since=<timestamp>` for new critical actions
7. **NotificationBell real data** — Replace mock notifications with API-fetched alerts
8. **Toast alerts for critical actions** — When new critical action appears, show toast overlay

**Shared:**
9. **Theme alignment** — CSM (light) and VP CS (dark) both use healthThresholds utility for consistent classification colors
10. **Accessibility pass** — Add aria-labels to interactive elements in both dashboards

### Acceptance Criteria
- VP CS sees real health trajectory chart with monthly scores
- VP CS can click summary card → drilldown to filtered account list
- CSM receives notification when new critical action is triggered
- Both dashboards pass basic accessibility audit (aria-labels, keyboard nav)

---

## Key Files

| Component | File |
|-----------|------|
| CSM Layout Switcher | `src/components/csm/CSMDashboard.tsx` |
| CSM Focus Flow | `src/components/csm/CSMFocusFlow.tsx` |
| CSM Cockpit | `src/components/csm/CSMCockpit.tsx` |
| VP CS Dashboard | `src/components/dashboard/VPCSDashboard.tsx` |
| Daily Actions API | `backend/verticals/dc2_s/api_routes.py` (get_csm_daily_actions) |
| CSM Scorecard API | `backend/verticals/dc2_s/api_routes.py` (csm_scorecard) |
| Team Capacity API | `backend/verticals/dc2_s/api_routes.py` (team_capacity) |
| Health History API | `backend/verticals/dc2_s/api_routes.py` (health_score_history) |

## Dependencies
- Health score calculation pipeline must be running (scores exist in DB)
- Playbook execution model (PlaybookExecutionV2) must be migrated
- Feature flag: `FEATURE_CSM_DASHBOARD=true` (already enabled)

## Risk
- **P0**: CSM empty state without backend — needs graceful "no data" messaging before design partner demo
- **P1**: 100+ account performance — may need virtualized lists (react-window) in Sprint 3
