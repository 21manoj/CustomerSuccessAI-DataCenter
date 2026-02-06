# Data Center Landing Page Strategy

## Overview
Design a Data Center-specific landing page with left-side navigation tabs, similar to SaaS (`CSPlatform.tsx`) but with DC-specific nomenclature and content.

---

## Current State Analysis

### SaaS Tabs (from `CSPlatform.tsx`):
1. **Customer Success Performance Console** (`dashboard`)
2. **Data Integration** (`upload`)
3. **Customer Success Value Analytics** (`analytics`)
4. **Account Health** (`accounts`)
5. **Product Health** (`products`)
6. **AI Insights** (`rag-analysis`)
7. **CS AI Agents** (`insights`)
8. **Settings** (`settings`)
9. **Reports** (`reports`)

### Existing DC Components (with `_dc` suffix):
- ✅ `Dashboard_dc.tsx` - Main DC dashboard (has tabs but needs restructuring)
- ✅ `TenantList_dc.tsx` - Tenant listing
- ✅ `TenantDetails_dc.tsx` - Tenant detail view
- ✅ `HealthScore_dc.tsx` - Health score component
- ✅ `KPICard_dc.tsx` - KPI card component
- ✅ `KPIChart_dc.tsx` - KPI chart component
- ✅ `PlaybookPanel_dc.tsx` - Playbook panel
- ✅ `AlertBanner_dc.tsx` - Alert banner

### Shared Components (used by both SaaS and DC):
- `RAGAnalysis.tsx` - AI Insights (can be reused)
- `SignalAnalyst.tsx` - Signal analysis (can be reused)
- `Settings.tsx` - Settings modal (needs DC-specific version)
- `Playbooks.tsx` - Playbooks (needs DC-specific version)
- `PlaybookReports.tsx` - Playbook reports (needs DC-specific version)

---

## Proposed DC Landing Page Tabs Structure

### Tab Mapping: SaaS → DC Nomenclature

| SaaS Tab | DC Tab Name | DC Tab ID | Status | Components |
|----------|-------------|-----------|--------|------------|
| Customer Success Performance Console | **Data Center Operations Console** | `dashboard` | ✅ Exists | `Dashboard_dc.tsx` (needs refactor) |
| Data Integration | **Data Integration** | `upload` | ⚠️ Partial | Reuse SaaS upload logic, DC-specific validation |
| Customer Success Value Analytics | **Tenant Performance Analytics** | `analytics` | ⚠️ Partial | `TenantList_dc.tsx`, `TenantDetails_dc.tsx`, `KPIChart_dc.tsx` |
| Account Health | **Tenant Health** | `tenants` | ✅ Exists | `TenantList_dc.tsx`, `HealthScore_dc.tsx`, `TenantDetails_dc.tsx` |
| Product Health | **Infrastructure Health** | `infrastructure` | ❌ Pending | Need to build `InfrastructureHealth_dc.tsx` |
| AI Insights | **AI Insights** | `rag-analysis` | ✅ Exists | `RAGAnalysis.tsx` (reuse) |
| CS AI Agents | **Signal Analyst** | `signals` | ✅ Exists | `SignalAnalyst.tsx` (reuse) |
| Settings | **Settings** | `settings` | ❌ Pending | Need `Settings_dc.tsx` |
| Reports | **Playbooks & Reports** | `playbooks` | ⚠️ Partial | `PlaybookPanel_dc.tsx` exists, need `PlaybookReports_dc.tsx` |

---

## Detailed Tab Breakdown

### 1. **Data Center Operations Console** (`dashboard`)
**Nomenclature:** "Operations Console" (vs SaaS "Performance Console")

**Components:**
- ✅ `Dashboard_dc.tsx` (main component)
- ✅ `KPICard_dc.tsx` (KPI cards)
- ✅ `HealthScore_dc.tsx` (health score summary)
- ✅ `AlertBanner_dc.tsx` (critical alerts)
- ✅ `TenantList_dc.tsx` (quick tenant overview)

**Content:**
- Overall tenant health summary
- Critical alerts (infrastructure issues, SLA breaches)
- Top KPIs across 5 pillars (P1-P5)
- Recent playbook executions
- Infrastructure status overview

**Status:** ✅ **Built** (needs refactoring to match tab structure)

---

### 2. **Data Integration** (`upload`)
**Nomenclature:** Same as SaaS (universal concept)

**Components:**
- Reuse SaaS upload logic
- DC-specific validation (account ID ranges, KPI definitions)
- Excel template validation for DC2_S structure

**Content:**
- Upload CSV/Excel files (accounts, KPIs, signals, products, profiles)
- Data validation feedback
- Import history

**Status:** ⚠️ **Partial** (reuse SaaS, add DC validation)

---

### 3. **Tenant Performance Analytics** (`analytics`)
**Nomenclature:** "Tenant Performance" (vs SaaS "Account Health")

**Components:**
- ✅ `TenantList_dc.tsx` (tenant listing with filters)
- ✅ `TenantDetails_dc.tsx` (detailed tenant view)
- ✅ `KPIChart_dc.tsx` (KPI trend charts)
- ✅ `HealthScore_dc.tsx` (health score breakdown)

**Content:**
- Tenant list with health scores
- Filter by industry, region, tier
- KPI trends over time
- Health score trends
- Comparative analytics

**Status:** ✅ **Built** (needs integration into tab structure)

---

### 4. **Tenant Health** (`tenants`)
**Nomenclature:** "Tenant Health" (vs SaaS "Account Health")

**Components:**
- ✅ `TenantList_dc.tsx` (main list view)
- ✅ `TenantDetails_dc.tsx` (detail view)
- ✅ `HealthScore_dc.tsx` (health score component)
- ✅ `KPICard_dc.tsx` (KPI cards per tenant)

**Content:**
- Tenant health dashboard
- Health score breakdown by pillar
- At-risk tenant identification
- Health trend analysis

**Status:** ✅ **Built** (needs integration)

---

### 5. **Infrastructure Health** (`infrastructure`)
**Nomenclature:** "Infrastructure Health" (vs SaaS "Product Health")

**Components:**
- ❌ `InfrastructureHealth_dc.tsx` (NEW - needs to be built)
- Reuse `ProductHealth` concepts but adapt for DC infrastructure

**Content:**
- Infrastructure component health (servers, cooling, power, network)
- Uptime metrics
- Capacity utilization
- Performance metrics by infrastructure type
- Alert history

**Status:** ❌ **Pending** (needs to be built)

---

### 6. **AI Insights** (`rag-analysis`)
**Nomenclature:** Same as SaaS (universal concept)

**Components:**
- ✅ `RAGAnalysis.tsx` (reuse as-is)

**Content:**
- Natural language queries about tenant data
- Historical analysis
- Trend insights
- Anomaly detection

**Status:** ✅ **Built** (reuse existing)

---

### 7. **Signal Analyst** (`signals`)
**Nomenclature:** "Signal Analyst" (vs SaaS "CS AI Agents")

**Components:**
- ✅ `SignalAnalyst.tsx` (reuse as-is)

**Content:**
- Qualitative signal analysis
- Email sentiment
- Meeting notes analysis
- Escalation patterns
- Signal trends

**Status:** ✅ **Built** (reuse existing)

---

### 8. **Settings** (`settings`)
**Nomenclature:** Same as SaaS (universal concept)

**Components:**
- ❌ `Settings_dc.tsx` (NEW - needs to be built)
- Reuse: `OpenAIKeySettings.tsx`, `PlaybookAutomationSettings.tsx`, `GovernanceSettings.tsx`
- Need DC-specific settings

**Content:**
- **DC-Specific Settings:**
  - Pillar weights configuration (P1-P5)
  - KPI definitions and thresholds
  - Account ID range configuration
  - Infrastructure monitoring settings
  - SLA thresholds
- **Common Settings:**
  - OpenAI API key
  - Playbook automation
  - Governance & audit logs
  - User management

**Status:** ❌ **Pending** (needs to be built)

---

### 9. **Playbooks & Reports** (`playbooks`)
**Nomenclature:** "Playbooks & Reports" (vs SaaS "Reports")

**Components:**
- ✅ `PlaybookPanel_dc.tsx` (playbook panel)
- ⚠️ `PlaybookReports.tsx` (exists but may need DC-specific version)
- ❌ `PlaybookReports_dc.tsx` (may need DC-specific version)

**Content:**
- Active playbooks
- Playbook execution history
- Playbook effectiveness metrics
- Custom reports
- Export capabilities

**Status:** ⚠️ **Partial** (playbook panel exists, reports need review)

---

## Pending Work Summary

### ❌ **Not Built Yet:**

1. **`InfrastructureHealth_dc.tsx`**
   - Infrastructure component health dashboard
   - Uptime metrics
   - Capacity utilization
   - Performance metrics

2. **`Settings_dc.tsx`**
   - DC-specific settings page
   - Pillar weights configuration
   - KPI definitions management
   - Account ID range settings
   - Infrastructure monitoring settings

3. **`PlaybookReports_dc.tsx`** (if needed)
   - DC-specific playbook reports
   - Infrastructure-focused metrics

### ⚠️ **Needs Refactoring:**

1. **`Dashboard_dc.tsx`**
   - Currently has inline tabs
   - Needs to be restructured to use left-side navigation
   - Extract tab content into separate components

2. **Upload Tab**
   - Reuse SaaS upload logic
   - Add DC-specific validation
   - DC-specific templates

3. **Analytics Tab**
   - Integrate existing components (`TenantList_dc.tsx`, `TenantDetails_dc.tsx`)
   - Add analytics-specific views

---

## File Renaming Strategy

### Current Naming Convention:
- DC components: `*_dc.tsx` (e.g., `Dashboard_dc.tsx`, `TenantList_dc.tsx`)
- SaaS components: No suffix (e.g., `CSPlatform.tsx`, `Playbooks.tsx`)

### Proposed Strategy: Use `dc_` Prefix

**Rationale:**
- Consistent prefix makes DC components easy to identify
- Prevents naming conflicts
- Clear separation between SaaS and DC components
- Easier to grep/find DC-specific files

### Renaming Plan:

#### Phase 1: Core DC Components (Already have `_dc` suffix)
```
Dashboard_dc.tsx          → dc_Dashboard.tsx
TenantList_dc.tsx         → dc_TenantList.tsx
TenantDetails_dc.tsx      → dc_TenantDetails.tsx
HealthScore_dc.tsx        → dc_HealthScore.tsx
KPICard_dc.tsx            → dc_KPICard.tsx
KPIChart_dc.tsx           → dc_KPIChart.tsx
PlaybookPanel_dc.tsx      → dc_PlaybookPanel.tsx
AlertBanner_dc.tsx        → dc_AlertBanner.tsx
```

#### Phase 2: New DC Components (To be created)
```
InfrastructureHealth_dc.tsx  → dc_InfrastructureHealth.tsx
Settings_dc.tsx              → dc_Settings.tsx
PlaybookReports_dc.tsx       → dc_PlaybookReports.tsx (if needed)
```

#### Phase 3: Shared Components (Keep as-is, but check usage)
```
RAGAnalysis.tsx          → Keep (used by both)
SignalAnalyst.tsx         → Keep (used by both)
Settings.tsx              → Keep (SaaS-specific)
Playbooks.tsx             → Keep (SaaS-specific)
PlaybookReports.tsx       → Keep (SaaS-specific)
```

### Implementation Steps:

1. **Create new main DC platform component:**
   ```
   dc_Platform.tsx  (similar to CSPlatform.tsx)
   ```
   - Left-side navigation tabs
   - Tab content routing
   - DC-specific styling

2. **Rename existing components:**
   - Rename all `*_dc.tsx` → `dc_*.tsx`
   - Update all imports
   - Update `App.tsx` routing

3. **Create missing components:**
   - `dc_InfrastructureHealth.tsx`
   - `dc_Settings.tsx`
   - `dc_PlaybookReports.tsx` (if needed)

4. **Refactor `Dashboard_dc.tsx`:**
   - Extract tab content into separate components
   - Integrate into `dc_Platform.tsx` tab structure

---

## Component Organization Structure

### Proposed File Structure:
```
src/components/
├── dc_Platform.tsx                    # Main DC landing page (like CSPlatform.tsx)
├── dc_Dashboard.tsx                  # Operations Console tab content
├── dc_TenantList.tsx                 # Tenant listing
├── dc_TenantDetails.tsx              # Tenant detail view
├── dc_HealthScore.tsx                # Health score component
├── dc_KPICard.tsx                     # KPI card component
├── dc_KPIChart.tsx                    # KPI chart component
├── dc_PlaybookPanel.tsx               # Playbook panel
├── dc_AlertBanner.tsx                 # Alert banner
├── dc_InfrastructureHealth.tsx        # NEW: Infrastructure health
├── dc_Settings.tsx                    # NEW: DC settings page
├── dc_PlaybookReports.tsx             # NEW: DC playbook reports (if needed)
│
├── CSPlatform.tsx                     # SaaS platform (keep as-is)
├── RAGAnalysis.tsx                    # Shared: AI Insights
├── SignalAnalyst.tsx                  # Shared: Signal Analyst
├── Settings.tsx                       # SaaS settings (keep)
├── Playbooks.tsx                      # SaaS playbooks (keep)
└── PlaybookReports.tsx                # SaaS reports (keep)
```

---

## Tab Content Mapping

### `dc_Platform.tsx` Tab Structure:

```typescript
const tabs = [
  { 
    id: 'dashboard', 
    label: 'Data Center Operations Console', 
    icon: BarChart3,
    component: <dc_Dashboard />
  },
  { 
    id: 'upload', 
    label: 'Data Integration', 
    icon: Upload,
    component: <DataUpload /> // Reuse SaaS with DC validation
  },
  { 
    id: 'analytics', 
    label: 'Tenant Performance Analytics', 
    icon: Activity,
    component: <dc_TenantAnalytics /> // New wrapper component
  },
  { 
    id: 'tenants', 
    label: 'Tenant Health', 
    icon: Users,
    component: <dc_TenantHealth /> // New wrapper component
  },
  { 
    id: 'infrastructure', 
    label: 'Infrastructure Health', 
    icon: Zap,
    component: <dc_InfrastructureHealth /> // NEW
  },
  { 
    id: 'rag-analysis', 
    label: 'AI Insights', 
    icon: MessageSquare,
    component: <RAGAnalysis /> // Reuse
  },
  { 
    id: 'signals', 
    label: 'Signal Analyst', 
    icon: MessageSquare,
    component: <SignalAnalyst /> // Reuse
  },
  { 
    id: 'playbooks', 
    label: 'Playbooks & Reports', 
    icon: FileText,
    component: <dc_PlaybooksReports /> // New wrapper component
  },
  { 
    id: 'settings', 
    label: 'Settings', 
    icon: Settings,
    component: <dc_Settings /> // NEW
  }
];
```

---

## Implementation Priority

### Phase 1: Foundation (Week 1)
1. ✅ Create `dc_Platform.tsx` with left-side navigation
2. ✅ Rename existing `*_dc.tsx` → `dc_*.tsx`
3. ✅ Update imports and routing
4. ✅ Integrate existing DC components into tabs

### Phase 2: Missing Components (Week 2)
1. ❌ Build `dc_InfrastructureHealth.tsx`
2. ❌ Build `dc_Settings.tsx`
3. ⚠️ Review and build `dc_PlaybookReports.tsx` if needed

### Phase 3: Refinement (Week 3)
1. ⚠️ Refactor `dc_Dashboard.tsx` to remove inline tabs
2. ⚠️ Integrate upload logic with DC validation
3. ⚠️ Create wrapper components for analytics/tenants tabs
4. ⚠️ Polish UI/UX for DC-specific content

---

## Key Differences: SaaS vs DC

| Aspect | SaaS | Data Center |
|--------|------|-------------|
| **Primary Entity** | Accounts | Tenants |
| **Health Focus** | Account health, product usage | Tenant health, infrastructure |
| **KPIs** | SaaS metrics (adoption, NPS) | Infrastructure KPIs (uptime, cooling, power) |
| **Pillars** | Generic SaaS pillars | DC2_S 5-Pillar Model (P1-P5) |
| **Playbooks** | Account-focused | Infrastructure & tenant-focused |
| **Reports** | Account performance | Infrastructure & tenant performance |

---

## Next Steps

1. **Review this strategy** with team
2. **Approve file renaming** approach (`dc_` prefix)
3. **Prioritize pending work** (Infrastructure Health, Settings)
4. **Create implementation tickets** for each phase
5. **Start with Phase 1** (foundation and renaming)

---

**Document Status:** Strategy Document (No Code Changes Yet)  
**Last Updated:** 2026-01-19  
**Next Review:** After team approval
