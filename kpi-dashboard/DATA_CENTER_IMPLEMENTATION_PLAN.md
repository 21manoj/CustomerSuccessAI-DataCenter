# Data Center Platform - Implementation Plan

## Executive Summary

Based on the detailed specification and answers to all questions, this document provides a comprehensive implementation plan for the 7-tab Data Center platform.

---

## ✅ Answers Summary

### File Naming
- **DC-specific:** `dc_*.tsx` prefix (e.g., `dc_Platform.tsx`, `dc_TenantHub.tsx`)
- **Shared:** No prefix (e.g., `SignalAnalyst.tsx`, `RAGAnalysis.tsx`)

### Component Strategy
- **TenantHub:** Wrapper around existing `TenantList_dc.tsx`
- **TenantPlacard:** New `dc_TenantPlacard.tsx` (DC-specific)
- **Sub-tabs:** Horizontal tabs below placard
- **Placard:** Sticky with collapse option

### Routing
- **Main tabs:** React Router routes (`/dc-dashboard/tenants`)
- **Sub-tabs:** Query params (`?tab=journey`)
- **Deep linking:** Supported for tenant detail views

---

## 📊 API Endpoint Investigation Results

### ✅ **EXISTING Endpoints (Verified)**

| Endpoint | Status | Location | Notes |
|----------|--------|----------|-------|
| `POST /api/upload` | ✅ Exists | `upload_api.py` | Needs `upload_mode` param |
| `POST /api/onboarding/upload` | ✅ Exists | `onboarding_api.py` | For onboarding flow |
| `POST /api/onboarding/validate-excel` | ✅ Exists | `onboarding_api.py` | Excel validation |
| `GET /api/data/status` | ✅ Exists | `data_management_api.py` | Returns data status |
| `GET /api/kpi-reference-ranges` | ✅ Exists | `kpi_reference_ranges_api.py` | Reference ranges |
| `GET /api/accounts` | ✅ Exists | `kpi_api.py` | List accounts (SaaS filter) |
| `GET /api/accounts/<id>` | ✅ Exists | `kpi_api.py` | Account details |
| `GET /api/journey/*` | ⚠️ Partial | `journey_viz_api.py` | Need to verify exact endpoints |
| `GET /api/admin/*` | ❓ Unknown | Need to verify | Admin endpoints need investigation |

### ❌ **MISSING Endpoints (Need to Build)**

| Endpoint | Priority | Purpose |
|----------|----------|---------|
| `POST /api/data/upload` (enhanced) | 🔴 High | Add `upload_mode` param (Append/Upsert/Merge/Full) |
| `GET /api/data/upload-history` | 🔴 High | List past uploads |
| `POST /api/data/trigger-wizard-a` | 🔴 High | Trigger Wizard A asynchronously |
| `GET /api/data/wizard-a/status/<task_id>` | 🔴 High | Poll Wizard A progress |
| `GET /api/journey/accounts` | 🟡 Medium | List accounts with journey data | Adapt from `/api/wizard/runs` or create new |
| `GET /api/journey/:accountId` | 🟡 Medium | Full journey for one account | Adapt from `/api/wizard/account/` or create new |
| `GET /api/journey/:accountId/kpis` | 🟡 Medium | KPI details with 3-level rollups | Build new endpoint |
| `GET /api/journey/:accountId/infra` | 🟡 Medium | Infrastructure health data (P2 KPIs) | Build new endpoint |
| `GET /api/admin/summary` | 🟡 Medium | Admin overview stats | Build or verify existing |
| `GET /api/admin/wizard-b/patterns` | 🟡 Medium | Pattern profiles from Wizard B | Build or verify existing |
| `GET /api/admin/wizard-b/warnings` | 🟡 Medium | Early warning rules | Build or verify existing |
| `GET /api/admin/wizard-c/weights` | 🟡 Medium | Learned weights from Wizard C | Build or verify existing |
| `POST /api/admin/wizard-c/recalibrate` | 🟡 Medium | Trigger Wizard C recalibration | Build or verify existing |

---

## 🏗️ Implementation Phases

### **Phase 1: Foundation (Week 1) - 8 hours**

#### 1.1 Create Component Structure
```
src/components/
├── dc/
│   ├── platform/
│   │   └── dc_Platform.tsx          ← Main 7-tab container
│   ├── tenants/
│   │   ├── dc_TenantHub.tsx         ← Tab 2 wrapper
│   │   ├── dc_TenantPlacard.tsx     ← Tenant summary card
│   │   └── dc_TenantKPIDetails.tsx  ← 3-level rollup display
│   ├── data-integration/
│   │   └── dc_DataIntegration.tsx   ← Tab 6 container
│   └── settings/
│       └── dc_Settings.tsx           ← Tab 7 container
└── shared/                           ← Move shared components here
    ├── SignalAnalyst.tsx
    ├── RAGAnalysis.tsx
    └── AdminDashboard.tsx
```

**Tasks:**
- [ ] Create folder structure
- [ ] Build `dc_Platform.tsx` with 7-tab navigation
- [ ] Set up React Router routes
- [ ] Move shared components to `shared/` folder
- [ ] Update imports across codebase

**Dependencies:** None

---

#### 1.2 Integrate Existing Tabs
- [ ] Tab 1: Import `ExecutiveDashboard.tsx` (no changes)
- [ ] Tab 3: Import `SignalAnalyst.tsx` (no changes)
- [ ] Tab 4: Import `RAGAnalysis.tsx` (no changes)
- [ ] Tab 5: Import `AdminDashboard.tsx` (no changes)

**Dependencies:** 1.1

---

### **Phase 2: Tenant Hub (Week 1-2) - 12 hours**

#### 2.1 Build TenantHub Wrapper
```typescript
// dc_TenantHub.tsx
- Import TenantList_dc.tsx
- Handle tenant selection
- Show TenantPlacard when tenant selected
- Render sub-tabs (Journey, Infrastructure, KPIs, Activity)
```

**Tasks:**
- [ ] Create `dc_TenantHub.tsx`
- [ ] Integrate `TenantList_dc.tsx` (no refactoring)
- [ ] Add tenant selection state management
- [ ] Add sub-tab navigation (horizontal tabs)

**Dependencies:** 1.1

---

#### 2.2 Build TenantPlacard
```typescript
// dc_TenantPlacard.tsx
- Display tenant summary (name, health score, status)
- Show 5 pillar mini-gauges
- Show ARR, renewal date, CSM info
- Quick action buttons
- Collapse/expand functionality
```

**Tasks:**
- [ ] Create `dc_TenantPlacard.tsx`
- [ ] Design placard UI (mirror SaaS AccountInfoPlacard)
- [ ] Add sticky positioning with collapse
- [ ] Integrate with TenantHub

**Dependencies:** 2.1

---

#### 2.3 Build TenantKPIDetails
```typescript
// dc_TenantKPIDetails.tsx
- Display 3-level health score calculation
- Show L1 weights (KPI → Pillar)
- Show L2 weights (Pillar → Account)
- Show reference ranges with visual bars
- Filter by pillar
```

**Tasks:**
- [ ] Create `dc_TenantKPIDetails.tsx`
- [ ] Build 3-level rollup display
- [ ] Integrate reference range API
- [ ] Add pillar filtering
- [ ] Add visual range indicators

**Dependencies:** 2.1, API endpoints

---

#### 2.4 Integrate Journey Timeline
- [ ] Import `JourneyDashboardV3.tsx` into TenantHub
- [ ] Add as "Journey" sub-tab
- [ ] Pass tenant account_id as prop

**Dependencies:** 2.1

---

#### 2.5 Build Infrastructure Health Sub-tab
```typescript
// dc_InfrastructureHealth.tsx
- Display infrastructure KPIs (P2: Operational Stability)
- Show: RMA Frequency, MTBF, Critical Incidents, Alert Response Time
- Infrastructure component status
- Uptime metrics
```

**Tasks:**
- [ ] Create `dc_InfrastructureHealth.tsx`
- [ ] Query P2 KPIs for selected tenant
- [ ] Display infrastructure metrics
- [ ] Add as "Infrastructure" sub-tab

**Dependencies:** 2.1, API endpoints

---

### **Phase 3: Data Integration Tab (Week 2) - 10 hours**

#### 3.1 Build Backend Upload Enhancement
```python
# Enhance upload_api.py
POST /api/data/upload
- Add upload_mode parameter: 'append', 'upsert', 'merge', 'full'
- Implement staging logic
- Add validation
- Return upload_id for tracking
```

**Tasks:**
- [ ] Add `upload_mode` parameter to `/api/data/upload`
- [ ] Create `staged_uploads` table
- [ ] Implement staging logic (database + filesystem)
- [ ] Add validation (schema, types, ranges, references)
- [ ] Implement merge conflict resolution (last-write-wins)

**Dependencies:** None (backend only)

---

#### 3.2 Build Upload History Endpoint
```python
GET /api/data/upload-history?customer_id={id}
- Returns list of past uploads
- Includes: upload_id, file_name, upload_mode, status, uploaded_at
```

**Tasks:**
- [ ] Create `upload_history` table (or use existing `kpi_uploads`)
- [ ] Build endpoint
- [ ] Add pagination

**Dependencies:** 3.1

---

#### 3.3 Build Wizard A Trigger Endpoint
```python
POST /api/data/trigger-wizard-a
- Accepts: customer_id, scope ('incremental' or 'full')
- Triggers Celery task
- Returns: task_id

GET /api/data/wizard-a/status/<task_id>
- Returns: status, progress, result
```

**Tasks:**
- [ ] Create Celery task for Wizard A
- [ ] Build trigger endpoint
- [ ] Build status polling endpoint
- [ ] Add progress tracking

**Dependencies:** None (backend only)

---

#### 3.4 Build Data Integration UI
```typescript
// dc_DataIntegration.tsx
- Upload panel (drag-drop)
- Upload mode selector (Full/Incremental)
- Incremental options (date range, merge mode)
- Upload progress
- Journey-aware post-upload prompt
- Upload history table
```

**Tasks:**
- [ ] Create `dc_DataIntegration.tsx`
- [ ] Build `UploadPanel.tsx` (drag-drop)
- [ ] Build `UploadModeSelector.tsx`
- [ ] Build `IncrementalOptions.tsx`
- [ ] Build `UploadProgress.tsx`
- [ ] Build `JourneyAwarePrompt.tsx`
- [ ] Build `UploadHistory.tsx`
- [ ] Integrate Wizard A trigger

**Dependencies:** 3.1, 3.2, 3.3

---

### **Phase 4: Journey API Endpoints (Week 2-3) - 8 hours**

#### 4.1 Build Journey Endpoints
```python
GET /api/journey/accounts
- List all accounts with journey data
- Returns: account_id, account_name, health_score, last_updated

GET /api/journey/:accountId
- Full journey timeline for one account
- Returns: journey events, phases, health history

GET /api/journey/:accountId/kpis
- KPI details with 3-level rollups
- Returns: KPIs with L1/L2 weights, reference ranges

GET /api/journey/:accountId/infra
- Infrastructure health data
- Returns: P2 KPIs, infrastructure metrics
```

**Tasks:**
- [ ] Create `journey_api.py` (or enhance existing)
- [ ] Build `/api/journey/accounts` endpoint
- [ ] Build `/api/journey/:accountId` endpoint
- [ ] Build `/api/journey/:accountId/kpis` endpoint
- [ ] Build `/api/journey/:accountId/infra` endpoint

**Dependencies:** None (backend only)

---

### **Phase 5: Settings Tab (Week 3) - 6 hours**

#### 5.1 Build Settings Component
```typescript
// dc_Settings.tsx
Sub-tabs:
- General Configuration (pillar weights, KPI definitions, reference ranges)
- Data Management (upload, Wizard A trigger, data sources)
- Integrations (OpenAI key, external sources)
- User Management (team, roles, notifications)
```

**Tasks:**
- [ ] Create `dc_Settings.tsx`
- [ ] Build General Configuration sub-tab
- [ ] Build Data Management sub-tab
- [ ] Build Integrations sub-tab (reuse existing modals)
- [ ] Build User Management sub-tab
- [ ] Add "Re-run Setup Wizard" button (modal overlay)

**Dependencies:** None

---

### **Phase 6: Integration & Testing (Week 3-4) - 8 hours**

#### 6.1 Integration Tasks
- [ ] Connect all tabs to APIs
- [ ] Add error handling
- [ ] Add loading states
- [ ] Add empty states
- [ ] Test deep linking
- [ ] Test navigation flows

#### 6.2 Testing
- [ ] Unit tests for components
- [ ] Integration tests for API endpoints
- [ ] E2E tests for critical flows
- [ ] Test with real data

**Dependencies:** All previous phases

---

## 📋 Detailed Task Breakdown

### Backend Tasks

| Task | File | Effort | Dependencies |
|------|------|--------|--------------|
| Add upload_mode to upload API | `upload_api.py` | 2h | None |
| Create staged_uploads table | Migration | 1h | None |
| Build upload history endpoint | `data_management_api.py` | 2h | Staged uploads table |
| Build Wizard A trigger endpoint | `data_management_api.py` | 3h | Celery setup |
| Build Wizard A status endpoint | `data_management_api.py` | 1h | Wizard A trigger |
| Build journey accounts endpoint | `journey_api.py` | 2h | None |
| Build journey detail endpoint | `journey_api.py` | 2h | None |
| Build journey KPIs endpoint | `journey_api.py` | 2h | None |
| Build journey infra endpoint | `journey_api.py` | 1h | None |

**Total Backend:** ~16 hours

---

### Frontend Tasks

| Task | File | Effort | Dependencies |
|------|------|--------|--------------|
| Create folder structure | - | 0.5h | None |
| Build dc_Platform.tsx | `dc/platform/dc_Platform.tsx` | 2h | None |
| Move shared components | - | 1h | None |
| Build dc_TenantHub.tsx | `dc/tenants/dc_TenantHub.tsx` | 3h | dc_Platform |
| Build dc_TenantPlacard.tsx | `dc/tenants/dc_TenantPlacard.tsx` | 3h | dc_TenantHub |
| Build dc_TenantKPIDetails.tsx | `dc/tenants/dc_TenantKPIDetails.tsx` | 4h | dc_TenantHub, APIs |
| Build dc_InfrastructureHealth.tsx | `dc/tenants/dc_InfrastructureHealth.tsx` | 3h | dc_TenantHub, APIs |
| Build dc_DataIntegration.tsx | `dc/data-integration/dc_DataIntegration.tsx` | 2h | dc_Platform |
| Build UploadPanel.tsx | `dc/data-integration/UploadPanel.tsx` | 2h | dc_DataIntegration |
| Build UploadModeSelector.tsx | `dc/data-integration/UploadModeSelector.tsx` | 1h | dc_DataIntegration |
| Build IncrementalOptions.tsx | `dc/data-integration/IncrementalOptions.tsx` | 1h | dc_DataIntegration |
| Build JourneyAwarePrompt.tsx | `dc/data-integration/JourneyAwarePrompt.tsx` | 1h | dc_DataIntegration |
| Build UploadHistory.tsx | `dc/data-integration/UploadHistory.tsx` | 2h | dc_DataIntegration, API |
| Build dc_Settings.tsx | `dc/settings/dc_Settings.tsx` | 4h | dc_Platform |
| Integration & testing | - | 4h | All components |

**Total Frontend:** ~32 hours

---

## 🎯 Critical Path

```
Phase 1 (Foundation)
    ↓
Phase 2 (Tenant Hub) ──┐
    ↓                  │
Phase 3 (Data Integration) ──┐
    ↓                         │
Phase 4 (Journey APIs) ───────┼──→ Phase 6 (Integration)
    ↓                         │
Phase 5 (Settings) ───────────┘
```

**Critical Path:** Phase 1 → Phase 2 → Phase 4 → Phase 6

---

## 📝 File Naming Convention

### ✅ **DC-Specific Components (dc_ prefix)**
```
dc_Platform.tsx
dc_TenantHub.tsx
dc_TenantPlacard.tsx
dc_TenantKPIDetails.tsx
dc_InfrastructureHealth.tsx
dc_DataIntegration.tsx
dc_Settings.tsx
```

### ✅ **Shared Components (no prefix)**
```
SignalAnalyst.tsx
RAGAnalysis.tsx
AdminDashboard.tsx
ExecutiveDashboard.tsx
JourneyDashboardV3.tsx
```

### ✅ **Existing DC Components (keep _dc suffix for now, migrate later)**
```
TenantList_dc.tsx        ← Keep as-is, import into dc_TenantHub
TenantDetails_dc.tsx     ← May be replaced by TenantHub sub-tabs
HealthScore_dc.tsx        ← Reuse in TenantPlacard
KPICard_dc.tsx            ← Reuse in TenantKPIDetails
KPIChart_dc.tsx           ← Reuse in TenantKPIDetails
PlaybookPanel_dc.tsx      ← May integrate into Settings or separate
AlertBanner_dc.tsx        ← Reuse in Executive Dashboard
```

---

## 🔧 Technical Decisions

### 1. **State Management**
- Use React `useState` for local component state
- Use React Router for navigation state
- Use URL query params for sub-tab state (`?tab=journey`)

### 2. **API Integration**
- Use `fetch` with `apiCall` utility
- Add error boundaries for API failures
- Implement retry logic for Wizard A polling

### 3. **Wizard A Execution**
- Use Celery for async execution
- Poll `/api/data/wizard-a/status/<task_id>` every 2 seconds
- Show progress bar in UI
- Handle errors gracefully

### 4. **Data Staging**
- Store upload metadata in `staged_uploads` table
- Store files temporarily in `data/staging/{customer_id}/{upload_id}/`
- Clean up staging files after merge (or after 7 days)

### 5. **Reference Ranges**
- Query from `kpi_reference_ranges` table
- Cache in frontend for performance
- Support customer-specific overrides

---

## 🚨 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API endpoints not ready | High | Build APIs first (Phase 3, 4) before UI |
| Wizard A takes too long | Medium | Show progress, allow cancellation |
| Large file uploads fail | Medium | Chunk uploads, resume capability |
| Deep linking breaks | Low | Test thoroughly, use React Router properly |
| Component naming conflicts | Low | Use `dc_` prefix consistently |

---

## 📊 Success Metrics

### Phase 1 Success:
- ✅ All 7 tabs render correctly
- ✅ Navigation works between tabs
- ✅ Existing components integrate without errors

### Phase 2 Success:
- ✅ Tenant list displays correctly
- ✅ Tenant selection shows placard
- ✅ Sub-tabs switch correctly
- ✅ Journey timeline displays

### Phase 3 Success:
- ✅ File upload works with all modes
- ✅ Upload history displays
- ✅ Wizard A triggers and completes
- ✅ Journey-aware prompt appears

### Phase 4 Success:
- ✅ All journey endpoints return correct data
- ✅ 3-level rollup calculation is accurate
- ✅ Reference ranges display correctly

### Phase 5 Success:
- ✅ Settings sub-tabs work
- ✅ Pillar weights can be configured
- ✅ Wizard A can be triggered from Settings

### Phase 6 Success:
- ✅ All tabs functional end-to-end
- ✅ No console errors
- ✅ Deep linking works
- ✅ Performance acceptable (< 2s load time)

---

## 🎬 Next Steps

1. **Review this plan** with team
2. **Confirm API endpoint status** (verify admin endpoints exist)
3. **Set up Celery** for Wizard A async execution
4. **Create database migrations** for staging tables
5. **Start Phase 1** (Foundation)

---

**Document Status:** Ready for Implementation  
**Total Estimated Effort:** ~48 hours (6 weeks @ 8h/week)  
**Start Date:** TBD  
**Target Completion:** TBD
