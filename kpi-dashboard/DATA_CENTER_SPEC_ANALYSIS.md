# Data Center Platform Specification - Analysis & Open Questions

## Analysis Summary

### ✅ **What's Clear:**
1. **7-tab structure** (consolidated from 9) - well-defined
2. **Tab 1: Executive Dashboard** - Already exists, reuse as-is
3. **Tab 2: Tenant Hub** - Clear pattern (mirrors SaaS Accounts)
4. **Tab 3-4: Signal Analyst & AI Insights** - Already exist, reuse
5. **Tab 5: Admin Insights** - Already exists, reuse
6. **Tab 6: Data Integration** - Detailed spec with incremental uploads
7. **Tab 7: Settings** - Clear sub-tabs structure
8. **Wizard placement** - A in Data Integration, B/C in Admin Insights
9. **3-level health score** - Detailed calculation transparency requirement

### ⚠️ **Areas Needing Clarification:**

---

## Open Questions

### 1. **Component Reuse & Naming**

**Question 1.1:** For `TenantHub.tsx`, should we:
- **Option A:** Build entirely new component from scratch?
- **Option B:** Refactor existing `TenantList_dc.tsx` and `TenantDetails_dc.tsx` into `TenantHub.tsx`?
- **Option C:** Keep `TenantList_dc.tsx` as-is and create `TenantHub.tsx` as a wrapper?

**Question 1.2:** For `TenantPlacard.tsx`, should we:
- **Option A:** Build new component based on SaaS `AccountInfoPlacard.tsx`?
- **Option B:** Adapt `AccountInfoPlacard.tsx` to work for both SaaS and DC?
- **Option C:** Create `dc_TenantPlacard.tsx` as DC-specific version?

**Question 1.3:** File naming consistency:
- Specification shows `TenantHub.tsx` (no `dc_` prefix)
- But strategy doc suggests `dc_*.tsx` prefix
- **Which naming convention should we follow?**
  - `TenantHub.tsx` (as in spec)
  - `dc_TenantHub.tsx` (as in strategy)
  - Or keep `*_dc.tsx` suffix?

---

### 2. **Executive Dashboard Integration**

**Question 2.1:** The spec says Tab 1 is `ExecutiveDashboard.tsx` which already exists. However:
- Current `ExecutiveDashboard.tsx` has tabs for "Health Scores" and "Data Quality"
- **Should Tab 1 show the full ExecutiveDashboard with its internal tabs?**
- **Or should Tab 1 show only the "Health Scores" tab content?**

**Question 2.2:** The spec mentions "Quick actions: 'View Journey' → navigates to Tenants tab"
- **Does this mean Executive Dashboard should have buttons that switch to Tab 2 (Tenants)?**
- **Or should it navigate to a tenant detail view within Tab 2?**

---

### 3. **Tenant Hub Architecture**

**Question 3.1:** Tenant Hub sub-tabs structure:
- Spec shows: Journey Timeline, Infrastructure, KPI Details, Activity History
- **Are these sub-tabs within TenantHub, or separate routes?**
- **Should they be:**
  - Horizontal tabs below placard?
  - Vertical tabs in sidebar?
  - Dropdown menu?

**Question 3.2:** TenantPlacard visibility:
- Spec says "always visible at top" when viewing tenant details
- **Should placard be:**
  - Fixed/sticky at top?
  - Scrollable with content?
  - Collapsible/expandable?

**Question 3.3:** Journey Timeline integration:
- Spec references `JourneyVisualizerV3.tsx`
- **Does this component already exist?** (I see `JourneyDashboardV3.tsx` in codebase)
- **Should we use `JourneyDashboardV3.tsx` or build new `JourneyVisualizerV3.tsx`?**

---

### 4. **3-Level Health Score Display**

**Question 4.1:** The spec shows detailed KPI rollup display with L1/L2 weights. For `TenantKPIDetails.tsx`:
- **Should this be a separate component or part of TenantPlacard?**
- **Should it show ALL KPIs or allow filtering by pillar?**

**Question 4.2:** Reference range display:
- Spec shows visual bars for Healthy/At-Risk/Critical ranges
- **Do we have reference ranges stored in database?**
- **What API endpoint provides reference ranges?** (`/api/kpi-reference-ranges`?)

**Question 4.3:** Weight transparency:
- Spec requires showing L1 weights (KPI → Pillar) and L2 weights (Pillar → Account)
- **Where are L1 weights stored?** (In KPI definitions? Database?)
- **Are L1 weights configurable per customer or fixed?**

---

### 5. **Data Integration Tab**

**Question 5.1:** Incremental upload modes:
- Spec shows: Append, Upsert, Merge, Full Refresh
- **Do these modes already exist in backend upload API?**
- **Or do we need to build this logic?**

**Question 5.2:** Journey-aware post-upload prompt:
- Spec shows prompt to "Run Wizard A" after upload
- **Should this trigger Wizard A automatically?**
- **Or just show a button that navigates to Settings → Data Management?**

**Question 5.3:** Upload history:
- Spec mentions "Past uploads table"
- **Does `/api/data/upload-history` endpoint exist?**
- **Or do we need to build it?**

**Question 5.4:** Data staging area:
- Spec mentions "STAGING AREA (data/staging)"
- **Is this a backend directory structure?**
- **Or a database table?**
- **How does data move from staging to raw data store?**

---

### 6. **Wizard A Integration**

**Question 6.1:** Wizard A trigger:
- Spec shows Wizard A can be triggered from:
  1. Data Integration tab (post-upload prompt)
  2. Settings → Data Management
- **Should Wizard A run:**
  - Synchronously (blocking UI)?
  - Asynchronously (background job with progress)?
  - Via API call or direct script execution?

**Question 6.2:** Wizard A API endpoint:
- Spec mentions `POST /api/data/trigger-wizard-a`
- **Does this endpoint exist?**
- **Or should we use existing `/api/onboarding/process-data`?**

**Question 6.3:** Wizard A scope:
- **Should Wizard A regenerate journeys for:**
  - All tenants?
  - Only tenants with new data?
  - User-selected tenants?

---

### 7. **Admin Insights Tab**

**Question 7.1:** Wizard B & C outputs:
- Spec references files: `pattern_profiles.json`, `early_warning_rules.json`, `learned_weights.json`
- **Where are these files stored?** (In customer directory? Database?)
- **What API endpoints serve this data?**

**Question 7.2:** Admin Insights sub-tabs:
- Spec shows: Overview, Pattern Analysis, Weight Calibration
- **Does `AdminDashboard.tsx` already have these sub-tabs?**
- **Or do we need to add them?**

**Question 7.3:** Weight recalibration:
- Spec shows "[Recalibrate Weights] button"
- **Does this trigger Wizard C automatically?**
- **Or does it navigate to a separate page?**

---

### 8. **Infrastructure Health Component**

**Question 8.1:** Infrastructure data source:
- Spec mentions "Infrastructure component health (servers, cooling, power, network)"
- **Do we have infrastructure data in the database?**
- **What tables/APIs provide infrastructure metrics?**

**Question 8.2:** Infrastructure KPIs:
- **Are infrastructure KPIs part of the 5-pillar model?**
- **Or are they separate metrics?**

**Question 8.3:** Infrastructure vs Product Health:
- SaaS has "Product Health" tab
- DC has "Infrastructure Health" sub-tab under Tenants
- **Should Infrastructure Health be:**
  - Only a sub-tab under Tenants?
  - Or also a standalone tab?
  - Or both?

---

### 9. **Settings Tab**

**Question 9.1:** Settings component scope:
- Spec shows sub-tabs: General Configuration, Data Management, Integrations, User Management
- **Should `dc_Settings.tsx` be:**
  - Completely new component?
  - Adaptation of existing `Settings.tsx`?
  - Wrapper around existing settings modals?

**Question 9.2:** Pillar weights configuration:
- Spec mentions "Default Pillar Weights (L2)"
- **Are these:**
  - Customer-specific (stored in `CustomerConfig`)?
  - Global defaults?
  - Both (defaults with customer overrides)?

**Question 9.3:** KPI definitions & thresholds:
- Spec mentions "KPI Definitions & Thresholds"
- **Do we have a UI for managing KPI definitions?**
- **Or is this just viewing existing definitions?**

**Question 9.4:** Re-run onboarding:
- Spec shows "[🔄 Re-run Setup Wizard] → Opens /onboarding route"
- **Should this:**
  - Open onboarding wizard in new tab/window?
  - Replace current view?
  - Show modal overlay?

---

### 10. **API Endpoints**

**Question 10.1:** Missing endpoints:
- Spec lists several API endpoints. **Which ones already exist?**
  - `POST /api/data/upload` - ✅ Exists?
  - `POST /api/data/validate` - ✅ Exists?
  - `GET /api/data/upload-history` - ❓ Exists?
  - `POST /api/data/trigger-wizard-a` - ❓ Exists?
  - `GET /api/data/status` - ❓ Exists?
  - `GET /api/journey/accounts` - ❓ Exists?
  - `GET /api/journey/:accountId` - ❓ Exists?
  - `GET /api/journey/:accountId/kpis` - ❓ Exists?
  - `GET /api/journey/:accountId/infra` - ❓ Exists?
  - `GET /api/admin/summary` - ❓ Exists?
  - `GET /api/admin/wizard-b/patterns` - ❓ Exists?
  - `GET /api/admin/wizard-b/warnings` - ❓ Exists?
  - `GET /api/admin/wizard-c/weights` - ❓ Exists?
  - `POST /api/admin/wizard-c/recalibrate` - ❓ Exists?

**Question 10.2:** Endpoint naming consistency:
- Some endpoints use `/api/data/*`, others `/api/journey/*`, others `/api/admin/*`
- **Is this the intended structure?**
- **Or should we consolidate under `/api/dc2s/*`?**

---

### 11. **Data Flow & Staging**

**Question 11.1:** Staging area implementation:
- Spec shows data flow: Upload → Staging → Validation → Merge → Raw Data Store
- **Is staging:**
  - A database table (`staging_uploads`)?
  - A file directory (`data/staging/`)?
  - In-memory processing?

**Question 11.2:** Validation logic:
- **What validations are needed?**
  - Schema validation (columns match)?
  - Data type validation?
  - Range validation (account IDs, dates)?
  - Reference validation (account exists, KPI defined)?

**Question 11.3:** Merge conflict resolution:
- Spec mentions "Smart merge with conflict resolution"
- **What are the conflict resolution rules?**
  - Last-write-wins?
  - User prompt for conflicts?
  - Automatic resolution based on timestamp?

---

### 12. **Component File Structure**

**Question 12.1:** New component organization:
- Spec shows components in `platform/`, `tenants/`, `data-integration/`, `settings/` folders
- **Should we:**
  - Create these new folders?
  - Keep everything in `components/` root?
  - Use `components/dc/` prefix folder?

**Question 12.2:** Shared vs DC-specific:
- Some components are shared (RAGAnalysis, SignalAnalyst)
- Others are DC-specific (TenantHub, InfrastructureHealth)
- **Should shared components be in `components/shared/`?**
- **Or keep them at root level?**

---

### 13. **Routing & Navigation**

**Question 13.1:** Route structure:
- Spec mentions routes like `/tenants`, `/tenants/:accountId`
- **Should these be:**
  - React Router routes (separate pages)?
  - Tab state within `dc_Platform.tsx`?
  - URL hash-based navigation (`#tenants`)?

**Question 13.2:** Deep linking:
- **Should tenant detail views be shareable URLs?**
- **Should tab state be preserved in URL?**
- **Example: `/dc-dashboard#tenants/29001/journey`?**

---

### 14. **Build Priority Clarification**

**Question 14.1:** The spec shows build priority with effort estimates. **Are these:**
- Developer hours?
- Story points?
- Calendar days?

**Question 14.2:** Dependencies:
- Priority 2 (`TenantHub.tsx`) depends on `TenantList_dc.tsx`
- **Should we refactor `TenantList_dc.tsx` first?**
- **Or build `TenantHub.tsx` and migrate later?**

---

### 15. **Testing & Validation**

**Question 15.1:** Test data:
- **Do we have test data for all scenarios?**
  - Multiple tenants with different health scores?
  - Infrastructure data?
  - Journey data?
  - Pattern analysis outputs?

**Question 15.2:** Validation:
- **Should we build validation UI before backend APIs?**
- **Or build APIs first, then UI?**

---

## Summary of Critical Questions

### 🔴 **Must Answer Before Coding:**

1. **File naming convention** (`dc_*.tsx` vs `*_dc.tsx` vs no prefix)
2. **API endpoint existence** (which endpoints need to be built)
3. **Component reuse strategy** (refactor vs new build)
4. **Data staging implementation** (database vs filesystem)
5. **Wizard A trigger mechanism** (API vs direct script execution)

### 🟡 **Should Answer Soon:**

6. **Tenant Hub sub-tab structure** (horizontal vs vertical)
7. **Infrastructure data source** (what tables/APIs exist)
8. **3-level weight storage** (where are L1 weights stored)
9. **Reference range API** (does it exist)
10. **Routing strategy** (React Router vs tab state)

### 🟢 **Can Answer During Implementation:**

11. **UI/UX details** (sticky placard, collapsible sections)
12. **Error handling** (validation failures, upload errors)
13. **Loading states** (progress indicators, spinners)
14. **Responsive design** (mobile/tablet support)

---

## Recommended Next Steps

1. **Review API endpoints** - Confirm which exist, which need building
2. **Clarify file naming** - Decide on `dc_*.tsx` vs `*_dc.tsx`
3. **Confirm component reuse** - Decide refactor vs new build
4. **Validate data sources** - Confirm infrastructure data availability
5. **Review Wizard integration** - Confirm trigger mechanisms
6. **Start with Priority 1** - Build `dc_Platform.tsx` foundation

---

**Document Status:** Analysis Complete - Awaiting Answers  
**Next Action:** Team review and answers to critical questions
