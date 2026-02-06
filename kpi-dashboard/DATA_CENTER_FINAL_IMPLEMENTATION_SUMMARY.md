# Data Center Platform - Final Implementation Summary

## 📋 Executive Summary

All questions have been answered. This document provides the final implementation plan with verified endpoint status and clear action items.

---

## ✅ All Questions Answered

### Critical Decisions Made:

1. **File Naming:** `dc_*.tsx` prefix for all DC-specific components
2. **TenantHub:** Wrapper around existing `TenantList_dc.tsx` (no refactoring)
3. **TenantPlacard:** New `dc_TenantPlacard.tsx` (DC-specific, mirror SaaS pattern)
4. **Sub-tabs:** Horizontal tabs below placard
5. **Routing:** React Router for main tabs, query params for sub-tabs
6. **Wizard A:** Async execution via Celery with progress polling
7. **Data Staging:** Database table + filesystem directory
8. **Infrastructure:** Part of P2 KPIs, sub-tab only (not standalone)

---

## 🔍 API Endpoint Status (Verified from Codebase)

### ✅ **CONFIRMED EXISTING**

| Endpoint | Location | Status | Notes |
|----------|----------|--------|-------|
| `POST /api/upload` | `upload_api.py` | ✅ Exists | Needs `upload_mode` enhancement |
| `POST /api/onboarding/upload` | `onboarding_api.py` | ✅ Exists | For onboarding flow |
| `POST /api/onboarding/validate-excel` | `onboarding_api.py` | ✅ Exists | Excel validation |
| `GET /api/data/status` | `data_management_api.py` | ✅ Exists | Returns data status |
| `GET /api/kpi-reference-ranges` | `kpi_reference_ranges_api.py` | ✅ Exists | Reference ranges |
| `GET /api/accounts` | `kpi_api.py` | ✅ Exists | **Note:** Has SaaS filter, may need DC version |
| `GET /api/accounts/<id>` | `kpi_api.py` | ✅ Exists | Account details |
| `GET /api/wizard/runs` | `journey_viz_api.py` | ✅ Exists | List wizard runs |
| `GET /api/wizard/journey/<run_id>` | `journey_viz_api.py` | ✅ Exists | Journey by run |
| `GET /api/wizard/account/<run_id>/<account_id>` | `journey_viz_api.py` | ✅ Exists | Account detail by run |
| `GET /api/journey/<account_id>` | `customer17_journey_api.py` | ✅ Exists | **Customer 17 specific** |

### ⚠️ **NEEDS INVESTIGATION**

| Endpoint | Status | Action Needed |
|----------|--------|---------------|
| `GET /api/admin/summary` | ❓ Unknown | Check if `AdminDashboard.tsx` exists and what APIs it uses |
| `GET /api/admin/wizard-b/patterns` | ❓ Unknown | Verify if Wizard B outputs are accessible via API |
| `GET /api/admin/wizard-b/warnings` | ❓ Unknown | Verify if early warning rules are accessible |
| `GET /api/admin/wizard-c/weights` | ❓ Unknown | Verify if learned weights are accessible |
| `POST /api/admin/wizard-c/recalibrate` | ❓ Unknown | Verify if Wizard C trigger exists |

**Finding:** No `AdminDashboard.tsx` component found in frontend. Need to verify:
- Does it exist under a different name?
- Is it part of another component?
- Do we need to build it?

### ❌ **CONFIRMED MISSING (Need to Build)**

| Endpoint | Priority | Effort | Purpose |
|----------|----------|--------|---------|
| `POST /api/data/upload` (enhanced) | 🔴 High | 2h | Add `upload_mode` param |
| `GET /api/data/upload-history` | 🔴 High | 2h | List past uploads |
| `POST /api/data/trigger-wizard-a` | 🔴 High | 3h | Trigger Wizard A async |
| `GET /api/data/wizard-a/status/<task_id>` | 🔴 High | 1h | Poll progress |
| `GET /api/journey/accounts` | 🟡 Medium | 2h | List accounts with journey (or adapt existing) |
| `GET /api/journey/:accountId` | 🟡 Medium | 2h | Full journey for account (or adapt existing) |
| `GET /api/journey/:accountId/kpis` | 🟡 Medium | 2h | KPI details with 3-level rollups |
| `GET /api/journey/:accountId/infra` | 🟡 Medium | 1h | Infrastructure health (P2 KPIs) |

**Total Missing Backend:** ~15 hours

---

## 🎯 Key Findings & Decisions

### 1. Journey API Path Mismatch

**Issue:** 
- Spec requires `/api/journey/*` endpoints
- Existing API uses `/api/wizard/*` (run-based, not account-based)
- Customer 17 has `/api/journey/<account_id>` but it's customer-specific

**Decision:** 
- **Option A (Recommended):** Create new account-based `/api/journey/*` endpoints
- **Option B:** Adapt existing `/api/wizard/*` endpoints
- **Option C:** Use customer-specific journey API pattern (dynamic registration)

**Recommendation:** **Option A** - Create unified account-based journey API that works for all customers

---

### 2. Admin Dashboard Component

**Finding:** 
- No `AdminDashboard.tsx` found in frontend
- Spec says Tab 5 uses `AdminDashboard.tsx` which "already exists"

**Action Required:**
- **Verify:** Does `AdminDashboard.tsx` exist? (Check if it's named differently)
- **If missing:** Build `AdminDashboard.tsx` with Wizard B/C sub-tabs
- **If exists:** Locate and verify it has Wizard B/C sub-components

---

### 3. Account vs Tenant Terminology

**Clarification:**
- Backend database uses "accounts" (`accounts` table)
- Frontend spec uses "tenants" (DC-specific terminology)
- API endpoints currently use "accounts"

**Decision:**
- **Backend APIs:** Keep as `/api/accounts/*` (database consistency)
- **Frontend:** Use "tenant" terminology in UI
- **Mapping:** Frontend maps "tenant" → "account" internally

---

### 4. Executive Dashboard Integration

**Finding:**
- `ExecutiveDashboard.tsx` exists and has internal tabs ("Health Scores" and "Data Quality")
- Spec says Tab 1 should show full Executive Dashboard

**Decision:**
- Import `ExecutiveDashboard.tsx` as-is
- Let it handle its own internal tab navigation
- No changes needed

---

## 📁 Component File Structure (Final)

```
src/components/
├── dc/                                    ← NEW: DC-specific folder
│   ├── platform/
│   │   └── dc_Platform.tsx                ← Main 7-tab container
│   ├── tenants/
│   │   ├── dc_TenantHub.tsx               ← Tab 2: Tenant hub wrapper
│   │   ├── dc_TenantPlacard.tsx           ← Tenant summary card (sticky)
│   │   ├── dc_TenantKPIDetails.tsx        ← 3-level rollup display
│   │   └── dc_InfrastructureHealth.tsx    ← Infrastructure sub-tab
│   ├── data-integration/
│   │   ├── dc_DataIntegration.tsx          ← Tab 6: Main container
│   │   ├── UploadPanel.tsx                ← Drag-drop upload
│   │   ├── UploadModeSelector.tsx          ← Full/Incremental toggle
│   │   ├── IncrementalOptions.tsx         ← Date range, merge mode
│   │   ├── UploadProgress.tsx             ← Progress bar
│   │   ├── JourneyAwarePrompt.tsx         ← Post-upload Wizard A prompt
│   │   ├── UploadHistory.tsx              ← Past uploads table
│   │   └── TemplateDownload.tsx           ← CSV templates
│   └── settings/
│       └── dc_Settings.tsx                 ← Tab 7: Settings page
│
├── shared/                                 ← NEW: Shared components folder
│   ├── SignalAnalyst.tsx                  ← Tab 3 (move from root)
│   ├── RAGAnalysis.tsx                    ← Tab 4 (move from root)
│   └── AdminDashboard.tsx                  ← Tab 5 (verify exists, move if found)
│
├── dashboard/
│   └── ExecutiveDashboard.tsx              ← Tab 1 (keep as-is)
│
└── [existing components...]
    ├── TenantList_dc.tsx                  ← Keep as-is, import into dc_TenantHub
    ├── TenantDetails_dc.tsx               ← May be replaced by TenantHub sub-tabs
    ├── HealthScore_dc.tsx                 ← Reuse in TenantPlacard
    ├── KPICard_dc.tsx                     ← Reuse in TenantKPIDetails
    ├── KPIChart_dc.tsx                    ← Reuse in TenantKPIDetails
    └── PlaybookPanel_dc.tsx               ← May integrate into Settings
```

---

## 🚨 Open Questions (Need Answers Before Coding)

### 1. Admin Dashboard Component
**Question:** Does `AdminDashboard.tsx` exist? If not, what should Tab 5 show?
- **Option A:** Build new `AdminDashboard.tsx` with Wizard B/C sub-tabs
- **Option B:** Use existing component (need to locate it)
- **Option C:** Create placeholder and build later

### 2. Journey API Approach
**Question:** Should we create new `/api/journey/*` endpoints or adapt existing `/api/wizard/*`?
- **Option A:** Create new account-based endpoints (cleaner API)
- **Option B:** Adapt existing run-based endpoints (faster)
- **Option C:** Use customer-specific pattern (dynamic registration)

### 3. Account/Tenant API Naming
**Question:** Should API endpoints use `/api/tenants/*` or `/api/accounts/*`?
- **Option A:** Keep `/api/accounts/*` (database consistency)
- **Option B:** Create `/api/tenants/*` adapter endpoints
- **Option C:** Use both (tenants proxy to accounts)

---

## 📊 Implementation Phases (Updated)

### **Phase 1: Foundation** (8 hours)
1. Create folder structure (`dc/`, `shared/`)
2. Build `dc_Platform.tsx` with 7-tab navigation
3. Set up React Router routes
4. Move shared components
5. Integrate existing tabs (1, 3, 4, 5)

### **Phase 2: Tenant Hub** (12 hours)
1. Build `dc_TenantHub.tsx` wrapper
2. Build `dc_TenantPlacard.tsx`
3. Build `dc_TenantKPIDetails.tsx` (3-level rollups)
4. Build `dc_InfrastructureHealth.tsx`
5. Integrate `JourneyDashboardV3.tsx`

### **Phase 3: Data Integration** (10 hours)
1. **Backend:** Enhance upload API with `upload_mode`
2. **Backend:** Build upload history endpoint
3. **Backend:** Build Wizard A trigger endpoints
4. **Frontend:** Build `dc_DataIntegration.tsx` and sub-components

### **Phase 4: Journey APIs** (8 hours)
1. **Backend:** Build account-based journey endpoints
2. **Backend:** Build KPI rollup endpoint
3. **Backend:** Build infrastructure endpoint

### **Phase 5: Settings** (6 hours)
1. Build `dc_Settings.tsx` with sub-tabs
2. Integrate existing settings modals
3. Add Wizard A trigger

### **Phase 6: Integration & Testing** (8 hours)
1. Connect all components to APIs
2. Add error handling
3. Test deep linking
4. E2E testing

**Total Estimated Effort:** ~52 hours (6.5 weeks @ 8h/week)

---

## 🎬 Ready to Start?

### ✅ **Pre-Implementation Checklist:**

- [x] All questions answered
- [x] File naming convention decided (`dc_*.tsx`)
- [x] Component strategy defined (wrapper approach)
- [x] Routing strategy defined (React Router + query params)
- [x] API endpoints investigated
- [ ] **Admin Dashboard component verified** (pending)
- [ ] **Journey API approach decided** (pending)
- [ ] **Account/Tenant API naming decided** (pending)

### 🔴 **Blockers (Need Answers):**

1. **Admin Dashboard:** Does it exist? What should Tab 5 show?
2. **Journey API:** Create new endpoints or adapt existing?
3. **API Naming:** Use `/api/accounts/*` or `/api/tenants/*`?

---

## 📝 Next Actions

1. **Verify Admin Dashboard** - Check if component exists or needs to be built
2. **Decide Journey API approach** - New endpoints vs adapt existing
3. **Confirm API naming** - Accounts vs Tenants in endpoints
4. **Start Phase 1** - Build foundation once blockers resolved

---

**Document Status:** Implementation Plan Complete - Pending 3 Decisions  
**Last Updated:** 2026-01-19  
**Ready for Coding:** After resolving 3 blockers above
