# DC vs SaaS Feature & Endpoint Audit Plan

## Overview
This document outlines the gaps and inconsistencies between the SaaS and DC (Data Center) dashboards, focusing on:
- Missing tabs/sections
- Missing API endpoints
- UI inconsistencies (playbooks, AI insights, etc.)
- Feature parity analysis

---

## 1. TAB/SECTION COMPARISON

### SaaS Tabs (CSPlatform.tsx)
1. **dashboard** - Customer Success Performance Console
2. **upload** - Data Integration
3. **analytics** - Customer Success Value Analytics
4. **accounts** - Account Health (uses AccountHealthDashboard component)
5. **products** - Product Health (uses ProductHealthDashboard component)
6. **rag-analysis** - AI Insights (uses RAGAnalysis component)
7. **insights** - CS AI Agents (uses Playbooks component)
8. **settings** - Settings (uses Settings component)
9. **reports** - Reports (likely uses PlaybookReports component)

### DC Tabs (Dashboard_dc.tsx)
1. **dashboard** - Data Center Dashboard ✅
2. **tenants** - Tenants ✅
3. **kpis** - KPIs ✅
4. **insights** - CS AI Agents (uses PlaybookPanel_dc component - SIMPLIFIED) ⚠️
5. **alerts** - Alerts (uses AlertBanner_dc component) ✅
6. **upload** - Data Integration ✅
7. **settings** - Settings ❌ (Placeholder only - "Data Center configuration settings")

### Missing DC Tabs
- ❌ **analytics** - Customer Success Value Analytics (no DC equivalent)
- ❌ **accounts** - Account Health (DC has "tenants" but different structure)
- ❌ **products** - Product Health (no DC equivalent - DC uses "tenants" instead)
- ❌ **rag-analysis** - AI Insights (no DC equivalent)
- ❌ **reports** - Reports (no DC equivalent)

---

## 2. API ENDPOINT ANALYSIS

### SaaS API Endpoints (from CSPlatform.tsx and related components)

#### Dashboard Tab
- `/api/accounts` - Get accounts
- `/api/kpis/customer/all` - Get all KPIs
- `/api/customer-performance/summary` - Performance summary
- `/api/health-trends` - Health trends
- `/api/time-series/stats` - Time series statistics
- `/api/health-status/kpis` - KPI health statuses

#### Analytics Tab
- `/api/accounts` - Get accounts
- `/api/health-trends?account_id=X` - Account-specific trends
- `/api/kpis/trends?kpi_name=X&account_id=Y` - KPI trends

#### Accounts Tab (AccountHealthDashboard)
- `/api/accounts` - Get accounts
- `/api/health-trends` - Health trends
- `/api/accounts/<id>/snapshots` - Account snapshots
- `/api/accounts/<id>` - Account details

#### Products Tab (ProductHealthDashboard)
- `/api/products` - Get products
- `/api/products/<id>/health` - Product health
- `/api/kpis/product/<id>` - Product KPIs

#### RAG Analysis Tab (RAGAnalysis component)
- `/api/rag-qdrant/build` - Build Qdrant knowledge base
- `/api/rag-qdrant/query` - Query Qdrant
- `/api/rag-qdrant/revenue-analysis` - Revenue analysis
- `/api/rag-historical/build` - Build historical knowledge base
- `/api/rag-historical/query` - Query historical data
- `/api/rag-temporal/query` - Query temporal data
- `/api/rag-openai/build` - Build OpenAI knowledge base
- `/api/rag-openai/query` - Query OpenAI

#### CS AI Agents/Playbooks Tab (Playbooks component)
- `/api/playbooks/recommendations/<playbook_id>` - POST - Get playbook recommendations
- `/api/playbooks/start` - POST - Start playbook execution
- `/api/playbooks/executions` - GET - Get playbook executions
- `/api/playbooks/executions/<id>/status` - GET - Get execution status
- `/api/playbooks/executions/<id>/step/<step_id>/execute` - POST - Execute step
- `/api/playbooks/triggers` - GET/POST - Playbook triggers
- `/api/playbooks/triggers/<id>` - GET/PUT/DELETE - Manage triggers

#### Reports Tab (PlaybookReports component)
- `/api/playbooks/reports` - GET - Get playbook reports
- `/api/playbooks/executions/<id>/report` - GET - Get execution report

#### Settings Tab
- Various settings endpoints (governance, MCP, etc.)

### DC API Endpoints (from Dashboard_dc.tsx and related components)

#### Dashboard Tab
- `/api/dc2s/accounts` - Get DC accounts ✅
- `/api/dc2s/kpis/all` - Get all DC KPIs ✅
- `/api/customer-performance/summary` - Performance summary (uses SaaS endpoint) ⚠️

#### Tenants Tab
- `/api/dc2s/accounts/<id>/kpis` - Get tenant KPIs ✅

#### KPIs Tab
- `/api/dc2s/kpis/all` - Get all KPIs ✅

#### CS AI Agents Tab (PlaybookPanel_dc)
- `/api/dc2s/recommendations/<account_id>` - GET - Get recommendations ✅

#### Alerts Tab (AlertBanner_dc)
- `/api/dc2s/alerts/<account_id>` - GET - Get alerts ✅

#### Health Score (HealthScore_dc)
- `/api/dc2s/health-score/<account_id>` - GET - Get health score ✅

---

## 3. FEATURE GAPS ANALYSIS

### Playbooks/CS AI Agents

#### SaaS (Playbooks component)
- ✅ Full playbook management UI
- ✅ Playbook definitions (voc-sprint, activation-blitz, sla-stabilizer, renewal-safeguard, expansion-timing)
- ✅ Account recommendations for each playbook
- ✅ Start playbook execution
- ✅ View playbook executions
- ✅ Execute playbook steps
- ✅ Configure playbook triggers
- ✅ Real-time execution status updates

#### DC (PlaybookPanel_dc component)
- ⚠️ **SIMPLIFIED** - Only shows recommendations
- ❌ No playbook execution functionality
- ❌ No playbook management
- ❌ No trigger configuration
- ❌ No execution status tracking
- ❌ Different recommendation format (pillar-based vs playbook-based)

**Gap:** DC only shows static recommendations, no actual playbook execution system.

---

### AI Insights/RAG Analysis

#### SaaS (RAGAnalysis component)
- ✅ Full RAG query interface
- ✅ Multiple vector DB support (Qdrant, historical, temporal, OpenAI)
- ✅ Knowledge base building
- ✅ Query templates
- ✅ Conversation history
- ✅ Revenue analysis queries
- ✅ Enhanced with MCP (external systems)
- ✅ Playbook-enhanced queries

#### DC
- ❌ **MISSING ENTIRELY** - No RAG/AI Insights tab
- ❌ No query interface
- ❌ No knowledge base integration
- ❌ No AI-powered insights

**Gap:** DC has no AI Insights/RAG analysis capability.

---

### Analytics

#### SaaS
- ✅ Customer Success Value Analytics tab
- ✅ Account health trends
- ✅ KPI trends over time
- ✅ Time series analysis
- ✅ Performance summaries

#### DC
- ❌ **MISSING** - No analytics tab
- ⚠️ Basic dashboard metrics only

**Gap:** DC lacks dedicated analytics section.

---

### Reports

#### SaaS
- ✅ Reports tab (PlaybookReports component)
- ✅ Playbook execution reports
- ✅ Report filtering and viewing
- ✅ Real-time report updates

#### DC
- ❌ **MISSING** - No reports tab
- ❌ No playbook execution reports (no playbooks to report on)

**Gap:** DC has no reporting capability.

---

### Settings

#### SaaS (Settings component)
- ✅ Governance settings
- ✅ MCP (Model Context Protocol) integration
- ✅ External system integration (Salesforce, ServiceNow, Surveys)
- ✅ KPI health settings
- ✅ Data quality settings
- ✅ Playbook automation settings

#### DC
- ⚠️ **NEEDS VERIFICATION** - Settings tab exists but content unknown
- ❌ Likely missing DC-specific settings

**Gap:** DC settings likely incomplete.

---

## 4. UI INCONSISTENCIES

### Playbooks/CS AI Agents

#### SaaS
- Full-featured playbook management interface
- Multi-step playbook execution
- Real-time status updates
- Account selector with recommendations
- Trigger configuration UI
- Execution history

#### DC
- Simple recommendation panel
- No execution UI
- No status tracking
- Basic priority-based display
- Pillar-based recommendations (not playbook-based)

**Inconsistency:** DC uses completely different playbook model (recommendations only, no execution).

---

### Health Score Display

#### SaaS
- Integrated in Account Health Dashboard
- Health trend charts
- Category breakdowns
- Portfolio overview

#### DC
- Standalone HealthScore_dc component
- Similar structure but may have different data format
- ⚠️ Needs verification of data consistency

---

### Alerts

#### SaaS
- Integrated in dashboard
- Account-level alerts
- KPI-based alerts

#### DC
- Dedicated AlertBanner_dc component
- Tenant-level alerts
- KPI status-based alerts

**Status:** ✅ Similar functionality, different implementation (acceptable).

---

## 5. PRIORITY GAPS TO ADDRESS

### High Priority
1. **RAG Analysis/AI Insights** - DC missing entirely
   - Impact: No AI-powered insights for DC users
   - Effort: High (need to adapt RAGAnalysis component for DC data)

2. **Playbook Execution** - DC only has recommendations
   - Impact: DC users can't execute playbooks
   - Effort: High (need playbook execution system for DC)

3. **Analytics Tab** - DC missing
   - Impact: Limited analytics capabilities
   - Effort: Medium (can adapt SaaS analytics)

4. **Reports Tab** - DC missing
   - Impact: No reporting capability
   - Effort: Medium (depends on playbook execution)

### Medium Priority
5. **Settings** - DC settings is just a placeholder
   - Impact: No configuration options available
   - Effort: High (needs full Settings component implementation)

6. **Product Health** - DC uses "Tenants" instead
   - Impact: Different data model (may be intentional)
   - Effort: Low (documentation/clarification needed)

### Low Priority
7. **Performance Summary** - DC uses SaaS endpoint
   - Impact: May not be DC-optimized
   - Effort: Low (create DC-specific endpoint if needed)

---

## 6. RECOMMENDATIONS

### Immediate Actions
1. **Audit DC Settings Tab** - Verify what's implemented
2. **Document Playbook Differences** - Clarify if DC recommendations are intentional simplification
3. **Create DC Analytics Endpoint** - Or confirm if DC analytics should use existing endpoints

### Short-term (1-2 weeks)
1. **Implement DC RAG Analysis** - Adapt RAGAnalysis component for DC data
2. **Create DC Analytics Tab** - Adapt analytics for DC-specific metrics
3. **Enhance DC Playbook Panel** - Add execution capability or document as "recommendations only"

### Long-term (1+ months)
1. **Full Playbook System for DC** - If playbook execution is needed
2. **DC Reports Tab** - If reporting is needed
3. **Unified Settings** - Consolidate settings across verticals

---

## 7. NEXT STEPS

1. ✅ Review this audit plan
2. ⏳ Verify DC Settings tab content
3. ⏳ Confirm playbook strategy (recommendations only vs full execution)
4. ⏳ Prioritize gaps based on business requirements
5. ⏳ Create detailed implementation plan for high-priority gaps
6. ⏳ Begin implementation

---

## 8. ENDPOINT MAPPING SUMMARY

### SaaS → DC Endpoint Mapping

| SaaS Endpoint | DC Equivalent | Status |
|--------------|---------------|--------|
| `/api/accounts` | `/api/dc2s/accounts` | ✅ Mapped |
| `/api/kpis/customer/all` | `/api/dc2s/kpis/all` | ✅ Mapped |
| `/api/health-trends` | `/api/dc2s/health-summary` | ⚠️ Partial (no trends) |
| `/api/playbooks/recommendations/<id>` | `/api/dc2s/recommendations/<account_id>` | ⚠️ Different format |
| `/api/playbooks/start` | ❌ Missing | ❌ No execution |
| `/api/playbooks/executions` | ❌ Missing | ❌ No execution |
| `/api/rag-qdrant/query` | ❌ Missing | ❌ No RAG |
| `/api/rag-qdrant/build` | ❌ Missing | ❌ No RAG |
| `/api/products` | ❌ Missing | ❌ No products in DC |
| `/api/playbooks/reports` | ❌ Missing | ❌ No reports |

---

*Last Updated: 2025-12-18*
*Auditor: AI Assistant*