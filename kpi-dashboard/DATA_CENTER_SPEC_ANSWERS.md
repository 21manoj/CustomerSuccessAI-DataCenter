# Data Center Specification - Answers & Verification

## ✅ All Questions Answered

This document consolidates all answers provided and verifies endpoint status from codebase investigation.

---

## 📋 Answers Summary

### 1. Component Reuse & Naming ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **TenantHub approach** | Option C: Wrapper around `TenantList_dc.tsx` | Create `dc_TenantHub.tsx` that imports and orchestrates |
| **TenantPlacard approach** | Option C: New `dc_TenantPlacard.tsx` | DC-specific version (mirror SaaS `AccountInfoPlacard.tsx`) |
| **File naming** | `dc_*.tsx` prefix | All DC components use `dc_` prefix |

### 2. Executive Dashboard ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Tab 1 content** | Full `ExecutiveDashboard.tsx` with internal tabs | Import as-is, no changes |
| **"View Journey" navigation** | Navigate to tenant detail in Tab 2 | Use React Router or tab state |

### 3. Tenant Hub Architecture ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Sub-tabs structure** | Horizontal tabs below placard | Use `<Tabs>` component horizontally |
| **Placard visibility** | Sticky at top with collapse option | `position: sticky; top: 0;` |
| **Journey component** | Use `JourneyDashboardV3.tsx` | Import existing component |

### 4. 3-Level Health Score ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **TenantKPIDetails placement** | Separate component in "KPIs" sub-tab | Not part of placard |
| **Reference ranges** | Database table, API exists | `GET /api/kpi-reference-ranges` |
| **L1 weight storage** | KPI definitions + customer overrides | Query `kpi_definitions` + `customer_kpi_weights` |

### 5. Data Integration ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Incremental upload modes** | Build backend logic | Add `upload_mode` param to `/api/upload` |
| **Journey-aware prompt** | Show button, trigger via API | Async execution with progress polling |
| **Upload history** | Build new endpoint | `GET /api/data/upload-history` |
| **Staging area** | Database table + filesystem | `staged_uploads` table + `data/staging/` |

### 6. Wizard A Integration ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Execution method** | Async via Celery, poll for progress | Background job with status endpoint |
| **API endpoint** | Create new `POST /api/data/trigger-wizard-a` | Don't reuse onboarding endpoint |
| **Scope** | Incremental (new data) or full (all tenants) | User-selectable scope parameter |

### 7. Admin Insights ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Wizard B/C outputs** | Customer directory + API | Files in `journey/` + API endpoints |
| **AdminDashboard sub-tabs** | Already has sub-tabs | Use existing component |
| **Recalibrate button** | Triggers Wizard C via API | Async execution, show progress |

### 8. Infrastructure Health ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Data source** | Part of KPI data (P2 KPIs) | Query P2 KPIs from same tables |
| **Infrastructure KPIs** | Yes, part of 5-pillar model (P2) | RMA Frequency, MTBF, Critical Incidents, etc. |
| **Tab placement** | Only sub-tab under Tenants | Not standalone tab |

### 9. Settings ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Settings component** | New `dc_Settings.tsx` | Can reuse some modals |
| **Pillar weights** | Global defaults + customer overrides | Query both, merge |
| **KPI definitions UI** | View + edit thresholds/ranges | Not full creation |
| **Re-run onboarding** | Modal overlay | Not new tab |

### 10. API Endpoints ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Endpoint naming** | Keep current structure | `/api/data/*`, `/api/journey/*`, `/api/admin/*` |
| **Missing endpoints** | See verified status below | Build missing ones |

### 11. Data Flow ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Staging** | Database table + filesystem | `staged_uploads` table + `data/staging/` |
| **Validation** | All types (schema, types, ranges, references) | Comprehensive validation |
| **Merge conflicts** | Last-write-wins with audit log | Update + log to `data_audit_log` |

### 12. Component Structure ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Folder organization** | Create new folders | `dc/platform/`, `dc/tenants/`, `dc/data-integration/`, `dc/settings/` |
| **Shared components** | Move to `components/shared/` | Organize shared components |

### 13. Routing ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Route structure** | React Router for tabs | `/dc-dashboard/tenants`, `/dc-dashboard/tenants/:accountId` |
| **Deep linking** | Yes, shareable URLs | Support query params for sub-tabs |

### 14. Build Priority ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Effort estimates** | Developer hours | ~48 hours total |
| **Dependencies** | Build wrapper, keep existing | No refactoring needed |

### 15. Testing ✅

| Question | Answer | Implementation |
|----------|--------|----------------|
| **Test data** | Yes, available | 30 tenants, 26 weeks data, Wizard B/C outputs |
| **Build order** | APIs first, then UI | Backend → Frontend |

---

## 🔍 API Endpoint Verification Results

### ✅ **VERIFIED EXISTING Endpoints**

| Endpoint | Status | Location | Verified |
|----------|--------|----------|----------|
| `POST /api/upload` | ✅ Exists | `upload_api.py` | ✅ Verified |
| `POST /api/onboarding/upload` | ✅ Exists | `onboarding_api.py` | ✅ Verified |
| `POST /api/onboarding/validate-excel` | ✅ Exists | `onboarding_api.py` | ✅ Verified |
| `GET /api/data/status` | ✅ Exists | `data_management_api.py` | ✅ Verified |
| `GET /api/kpi-reference-ranges` | ✅ Exists | `kpi_reference_ranges_api.py` | ✅ Verified |
| `GET /api/accounts` | ✅ Exists | `kpi_api.py` | ✅ Verified (SaaS filter) |
| `GET /api/accounts/<id>` | ✅ Exists | `kpi_api.py` | ✅ Verified |
| `GET /api/wizard/runs` | ✅ Exists | `journey_viz_api.py` | ✅ Verified (different path) |
| `GET /api/wizard/journey/<run_id>` | ✅ Exists | `journey_viz_api.py` | ✅ Verified |
| `GET /api/wizard/account/<run_id>/<account_id>` | ✅ Exists | `journey_viz_api.py` | ✅ Verified |

### ⚠️ **PARTIALLY EXISTS (Need Adaptation)**

| Endpoint | Current Status | Needed | Action |
|----------|----------------|--------|--------|
| `GET /api/journey/accounts` | ⚠️ Different path | `/api/wizard/runs` exists | Adapt or create new endpoint |
| `GET /api/journey/:accountId` | ⚠️ Different path | `/api/wizard/account/<run_id>/<account_id>` exists | Need account-focused endpoint |
| `GET /api/journey/:accountId/kpis` | ❌ Missing | Need 3-level rollup | Build new endpoint |
| `GET /api/journey/:accountId/infra` | ❌ Missing | Need P2 KPIs | Build new endpoint |

### ❌ **MISSING Endpoints (Need to Build)**

| Endpoint | Priority | Purpose | Estimated Effort |
|----------|----------|---------|------------------|
| `POST /api/data/upload` (enhanced) | 🔴 High | Add `upload_mode` param | 2h |
| `GET /api/data/upload-history` | 🔴 High | List past uploads | 2h |
| `POST /api/data/trigger-wizard-a` | 🔴 High | Trigger Wizard A async | 3h |
| `GET /api/data/wizard-a/status/<task_id>` | 🔴 High | Poll progress | 1h |
| `GET /api/journey/accounts` | 🟡 Medium | List accounts with journey | 2h |
| `GET /api/journey/:accountId` | 🟡 Medium | Full journey for account | 2h |
| `GET /api/journey/:accountId/kpis` | 🟡 Medium | KPI details with rollups | 2h |
| `GET /api/journey/:accountId/infra` | 🟡 Medium | Infrastructure health | 1h |
| `GET /api/admin/summary` | 🟡 Medium | Admin overview | 1h |
| `GET /api/admin/wizard-b/patterns` | 🟡 Medium | Pattern profiles | 1h |
| `GET /api/admin/wizard-b/warnings` | 🟡 Medium | Early warnings | 1h |
| `GET /api/admin/wizard-c/weights` | 🟡 Medium | Learned weights | 1h |
| `POST /api/admin/wizard-c/recalibrate` | 🟡 Medium | Trigger Wizard C | 1h |

**Total Backend Effort:** ~20 hours

---

## 📝 Key Implementation Notes

### Journey API Path Mismatch

**Issue:** Spec calls for `/api/journey/*` but existing API uses `/api/wizard/*`

**Current State:**
- `journey_viz_api.py` uses `/api/wizard/*` prefix
- Endpoints are run-based (`/api/wizard/journey/<run_id>`)
- Not account-based (`/api/journey/:accountId`)

**Solution Options:**
1. **Option A:** Create new `journey_api.py` with account-based endpoints
2. **Option B:** Adapt existing `journey_viz_api.py` to support both patterns
3. **Option C:** Use existing endpoints and add adapter layer in frontend

**Recommendation:** Option A - Create new account-based endpoints for cleaner API design

---

### Admin API Status

**Status:** ⚠️ **NEEDS VERIFICATION**

**Investigation Needed:**
- Check if `AdminDashboard.tsx` has sub-components for Wizard B/C
- Verify if admin API endpoints exist (may be in different file)
- Check if Wizard B/C outputs are accessible via API

**Action:** Investigate `AdminDashboard.tsx` component and related backend APIs

---

### Account vs Tenant Terminology

**Clarification Needed:**
- Backend uses "accounts" (database table: `accounts`)
- Frontend spec uses "tenants" (DC-specific terminology)
- **Question:** Should API endpoints use `/api/tenants/*` or `/api/accounts/*`?

**Recommendation:** 
- Keep backend as `/api/accounts/*` (database consistency)
- Frontend maps "tenant" to "account" internally
- Or create adapter endpoints `/api/tenants/*` that proxy to `/api/accounts/*`

---

## 🎯 Next Steps

1. ✅ **Verify Admin API endpoints** - Check if Wizard B/C endpoints exist
2. ✅ **Decide on Journey API approach** - New endpoints vs adapt existing
3. ✅ **Confirm account/tenant terminology** - API naming consistency
4. ✅ **Start Phase 1** - Build foundation (`dc_Platform.tsx`)

---

**Document Status:** Answers Consolidated, Endpoints Verified  
**Ready for Implementation:** Yes (pending Admin API verification)
