# Rollup Level Naming Change - Risk Assessment

**Date**: December 27, 2025  
**Proposed Change**: Reverse rollup level naming structure

## Current Structure

**Current Naming** (Bottom-up hierarchy):
- **Level 1 Rollup**: Individual KPI health scores (lowest level)
- **Level 2 Rollup**: Category-level health scores (middle level - Pillars)
- **Level 3 Rollup**: Overall corporate health score (top level - Final rollup)

## Proposed Change

**New Naming** (Top-down hierarchy):
- **Level 1**: Top level (Overall corporate health score) ← *Currently Level 3*
- **Level 2**: Pillar level (Category-level health scores) ← *Currently Level 2*
- **Level 3**: KPI level (Individual KPI health scores) ← *Currently Level 1*

**⚠️ CRITICAL**: This is a **REVERSAL** of the current numbering system!

---

## Risk Assessment

### 🔴 **HIGH RISK AREAS**

#### 1. **Frontend UI State Management** ⚠️ **HIGH RISK**

**Location**: `kpi-dashboard/src/components/CSPlatform.tsx`

**Impact**:
- Line 228: State type definition: `useState<'overview' | 'level1' | 'level2' | 'level3' | 'trends'>`
- Lines 3973-3977: Tab definitions with hardcoded labels and descriptions
- Lines 4167-4449: Tab content sections keyed by `activeRollupTab === 'level1'`, `'level2'`, `'level3'`

**Risk**: 
- **HIGH** - Multiple hardcoded string references to 'level1', 'level2', 'level3'
- Must update ALL conditional logic that checks these values
- State management depends on these exact string values
- Tab switching logic will break if not updated correctly

**Affected Code**:
```typescript
// Line 228
const [activeRollupTab, setActiveRollupTab] = useState<'overview' | 'level1' | 'level2' | 'level3' | 'trends'>('overview');

// Lines 3973-3977
{ id: 'level1', name: 'Level 1 Rollup', description: 'Individual KPI health scores & calculations' },
{ id: 'level2', name: 'Level 2 Rollup', description: 'Category-level health scores & weighted averages' },
{ id: 'level3', name: 'Level 3 Rollup', description: 'Overall corporate health score & final calculations' }

// Lines 4167, 4389, 4443
{activeRollupTab === 'level1' && ...}
{activeRollupTab === 'level2' && ...}
{activeRollupTab === 'level3' && ...}
```

**Required Changes**:
1. Update tab ID values (if changing semantics)
2. Update tab names and descriptions
3. Swap the conditional logic content blocks
4. Update TypeScript type definitions

**Breaking Risk**: ⚠️ **VERY HIGH** if tab IDs change (would break saved preferences, URLs, etc.)

---

#### 2. **Backend API Response Structure** ⚠️ **MEDIUM RISK**

**Location**: `kpi-dashboard/backend/corporate_api.py`

**Analysis**:
- Lines 175-392: `/api/corporate/rollup` endpoint
- Response structure does NOT explicitly include "level1", "level2", "level3" fields
- Returns: `category_scores`, `overall_score`, `maturity_tier`, etc.

**Risk**: 
- **LOW-MEDIUM** - Backend doesn't hardcode level names in response
- However, any documentation or API contracts that reference levels would need updating
- Frontend expects specific response structure that might be interpreted by level

**Required Changes**:
- Review API documentation
- Check if any API consumers depend on level naming
- Update any API documentation references

---

#### 3. **User Experience & Cognitive Model** ⚠️ **MEDIUM-HIGH RISK**

**Current Mental Model** (Bottom-up):
- Level 1 = Foundation (KPIs)
- Level 2 = Aggregation (Categories/Pillars)
- Level 3 = Final Result (Overall)

**New Mental Model** (Top-down):
- Level 1 = Final Result (Overall)
- Level 2 = Aggregation (Categories/Pillars)
- Level 3 = Foundation (KPIs)

**Risk**: 
- **MEDIUM-HIGH** - Users familiar with current system will be confused
- Reverses natural progression (detail → summary)
- Industry standard typically uses bottom-up numbering (1=detail, higher=aggregate)

**User Impact**:
- Existing users will need retraining
- Documentation updates required
- Training materials need revision
- Potential user errors due to confusion

---

#### 4. **Documentation & Training Materials** ⚠️ **MEDIUM RISK**

**Impact**:
- All documentation referencing "Level 1/2/3 Rollup" needs updating
- Training materials need revision
- User guides need rewriting
- API documentation updates
- Any external documentation or integrations

**Risk**: **MEDIUM** - High effort, low technical risk

---

### 🟡 **MEDIUM RISK AREAS**

#### 5. **RAG System Context** ✅ **LOW RISK**

**Location**: `kpi-dashboard/backend/enhanced_rag_qdrant.py`, RAG templates

**Analysis**:
- RAG system is schema-agnostic
- Uses semantic understanding, not hardcoded level names
- Queries about "rollup levels" would adapt naturally

**Risk**: **LOW** - RAG queries would adapt to new naming
**Action**: Minimal - may want to update example queries/templates

---

#### 6. **Database Schema** ✅ **NO RISK**

**Location**: `kpi-dashboard/backend/models.py`

**Analysis**:
- Database schema does NOT store level names
- Only stores: `category`, `kpi_parameter`, `aggregation_type`
- Level names are UI/presentation layer only

**Risk**: **NONE** - No database changes needed
**Action**: None required

---

#### 7. **Backend Calculation Logic** ✅ **NO RISK**

**Location**: `kpi-dashboard/backend/corporate_api.py`, `kpi_queries.py`

**Analysis**:
- Calculation logic does NOT reference "Level 1/2/3"
- Uses actual field names: `category`, `kpi_parameter`, `overall_score`
- Logic is data-driven, not label-driven

**Risk**: **NONE** - Calculations are independent of level names
**Action**: None required

---

### 🟢 **LOW RISK AREAS**

#### 8. **TypeScript Type Definitions** ⚠️ **LOW-MEDIUM RISK**

**Location**: `kpi-dashboard/src/components/CSPlatform.tsx:228`

**Impact**:
- TypeScript literal union type: `'overview' | 'level1' | 'level2' | 'level3' | 'trends'`
- Used for state management and type safety

**Risk**: **LOW-MEDIUM** - If changing tab IDs, type definition must change
**Action**: Update type definition if tab IDs change

---

#### 9. **URL Parameters / Browser History** ⚠️ **LOW RISK**

**Analysis**:
- If tab state is stored in URL or localStorage
- Saved preferences might break

**Risk**: **LOW** - Only affects users with saved preferences
**Action**: Consider migration logic for saved preferences

---

## Detailed Change Impact

### Frontend Changes Required

1. **CSPlatform.tsx** - Lines to update:
   - **Line 228**: Type definition (if changing semantics)
   - **Lines 3973-3977**: Tab configuration array (names/descriptions)
   - **Line 4167**: Level 1 tab content (currently Individual KPIs)
   - **Line 4389**: Level 2 tab content (currently Category-level)
   - **Line 4443**: Level 3 tab content (currently Overall)

2. **Content Swapping Required**:
   - Current "Level 1" content → Move to "Level 3"
   - Current "Level 2" content → Keep at "Level 2"
   - Current "Level 3" content → Move to "Level 1"

### Critical Decision Point

**⚠️ IMPORTANT QUESTION**: Do you want to change the **tab IDs** or just the **display labels**?

**Option A: Change IDs Only (Higher Risk)**
- Change `id: 'level1'` → `id: 'level3'` (semantics change)
- **PRO**: Maintains clean semantic alignment
- **CON**: Breaks saved preferences, URLs, any hardcoded references

**Option B: Change Labels Only (Lower Risk)** ✅ **RECOMMENDED**
- Keep `id: 'level1'` as-is
- Change `name: 'Level 1 Rollup'` → `name: 'Level 1: Overall Corporate Health'`
- Swap content blocks between tabs
- **PRO**: Minimal breaking changes
- **CON**: Tab IDs don't match semantics (minor inconsistency)

**Recommendation**: **Option B** - Change labels and swap content, keep IDs

---

## Risk Summary

| Area | Risk Level | Breaking Changes | Effort | Priority |
|------|-----------|------------------|--------|----------|
| Frontend UI State | 🔴 **HIGH** | Yes (if IDs change) | High | 1 |
| Backend API | 🟢 **LOW** | No | Low | 4 |
| Database Schema | 🟢 **NONE** | No | None | - |
| User Experience | 🟡 **MEDIUM** | Yes (cognitive) | Medium | 2 |
| Documentation | 🟡 **MEDIUM** | Yes | High | 3 |
| RAG System | 🟢 **LOW** | No | Low | 5 |
| Type Definitions | 🟡 **LOW** | Maybe | Low | 6 |

---

## Recommended Approach

### Phase 1: Assessment & Planning
1. ✅ **Confirm decision**: Change IDs vs. Labels only
2. ✅ **Review all frontend code** for level references
3. ✅ **Check for saved user preferences** (localStorage, URLs)
4. ✅ **Document current vs. new structure** clearly

### Phase 2: Implementation (If Approved)

**Recommended: Option B (Label Changes Only)**

1. **Frontend Updates** (`CSPlatform.tsx`):
   - Update tab names and descriptions (Lines 3973-3977)
   - Swap content blocks between level1 ↔ level3
   - Keep level2 content as-is
   - Keep tab IDs unchanged

2. **Testing**:
   - Test all tab switching
   - Verify content displays correctly
   - Check saved preferences still work
   - Verify calculations are unchanged

3. **Documentation**:
   - Update user guides
   - Update API documentation
   - Update training materials
   - Create migration guide for users

### Phase 3: Deployment
1. **Communication**: Notify users of change
2. **Deployment**: Deploy frontend changes
3. **Monitoring**: Watch for user confusion/errors
4. **Support**: Provide help documentation

---

## Alternative Consideration

**Question**: Why reverse the numbering? 

**Current (Bottom-up)** is more intuitive:
- Level 1 = Base data (KPIs) ✅ Natural progression
- Level 2 = Aggregation (Pillars)
- Level 3 = Final result (Overall)

**Proposed (Top-down)** reverses this:
- Level 1 = Final result (Overall)
- Level 2 = Aggregation (Pillars)
- Level 3 = Base data (KPIs)

**Industry Standard**: Most systems use bottom-up numbering (1 = detail, higher = aggregate)

**Consideration**: Could you achieve your goal with better labeling instead?
- "Level 1: Corporate Overview" (Overall)
- "Level 2: Category Breakdown" (Pillars)
- "Level 3: KPI Details" (Individual KPIs)

This would require reordering tabs, not reversing numbers.

---

## Final Risk Assessment

**Overall Risk Level**: 🟡 **MEDIUM-HIGH**

**Primary Risks**:
1. User confusion (cognitive model reversal)
2. Frontend code complexity (multiple hardcoded references)
3. Documentation/training updates (high effort)

**Technical Risk**: 🟢 **LOW** (if using Option B - labels only)

**Business Risk**: 🟡 **MEDIUM** (user retraining, potential confusion)

**Recommendation**: 
- ✅ **Proceed with caution** if business justification is strong
- ✅ **Use Option B** (label changes, keep IDs)
- ✅ **Plan for user communication** and support
- ⚠️ **Consider alternative**: Reorder tabs without reversing numbers

---

## Questions to Answer Before Proceeding

1. **Why reverse the numbering?** (Business justification)
2. **Change IDs or labels only?** (Technical decision)
3. **Timeline for user communication?** (Change management)
4. **Rollback plan?** (Risk mitigation)
5. **User acceptance testing plan?** (Quality assurance)

---

**Status**: ⏸️ **AWAITING DECISION** - No changes made, assessment complete

