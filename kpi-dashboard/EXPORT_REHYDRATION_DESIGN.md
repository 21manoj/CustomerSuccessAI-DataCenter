# Export & Rehydration Feature Design Document
## Multi-Tenant SaaS Security & Vertical Considerations

**Version:** 1.0  
**Date:** 2025-01-27  
**Status:** Design Phase

---

## Executive Summary

This document evaluates the current "Save Account Data to Excel" and "Data Rehydration" features for a multi-tenant SaaS environment. It identifies security requirements, potential risks, and design considerations for different verticals (Data Center, Marketplace, Corporate, etc.).

---

## Table of Contents

1. [Current Implementation Analysis](#current-implementation-analysis)
2. [Security Requirements](#security-requirements)
3. [Multi-Tenant Isolation Concerns](#multi-tenant-isolation-concerns)
4. [Export Feature Evaluation](#export-feature-evaluation)
5. [Rehydration Feature Evaluation](#rehydration-feature-evaluation)
6. [Vertical-Specific Considerations](#vertical-specific-considerations)
7. [Open Questions](#open-questions)
8. [Recommendations](#recommendations)
9. [Implementation Roadmap](#implementation-roadmap)

---

## Current Implementation Analysis

### Export Feature (`backend/export_api.py`)

**Current Endpoint:** `/api/export/all-account-data` (GET)

**What It Exports:**
- ✅ Accounts Summary (13 sheets total)
- ✅ All KPIs (account-level and product-level)
- ✅ Products
- ✅ Customer Profile Data (profile_metadata JSON)
- ✅ Playbook Triggers, Executions, Reports
- ✅ Customer Config
- ✅ Health Trends
- ✅ KPI Time Series
- ✅ KPI Reference Ranges
- ✅ Feature Toggles
- ✅ Export Metadata (includes Customer ID for validation)

**Security Features:**
- ✅ Filters by `customer_id` from session (`get_current_customer_id()`)
- ✅ Includes Customer ID in Export Metadata sheet
- ✅ Includes export timestamp and version

**Current Limitations:**
- ⚠️ No file encryption
- ⚠️ No access logging/audit trail
- ⚠️ No file size limits
- ⚠️ No rate limiting
- ⚠️ No expiration/retention policies

### Rehydration Feature (`backend/rehydration_api.py`)

**Current Endpoint:** `/api/rehydrate/import` (POST)

**What It Imports:**
- ✅ Accounts (with profile_metadata)
- ✅ Products
- ✅ KPIs (account-level and product-level)
- ✅ Customer Profile Data
- ✅ Playbook Triggers, Executions, Reports
- ✅ Customer Config
- ✅ Health Trends
- ✅ KPI Time Series
- ✅ KPI Reference Ranges
- ✅ Feature Toggles

**Security Features:**
- ✅ Validates Customer ID from Export Metadata
- ✅ Prevents cross-tenant imports (rejects if `export_customer_id != current_customer_id`)
- ✅ Requires Export Metadata sheet with Customer ID
- ✅ Validates export version
- ✅ Uses `get_current_customer_id()` for authentication

**Current Limitations:**
- ⚠️ **REPLACE MODE ONLY** - Deletes ALL existing data before import
- ⚠️ No dry-run/preview mode
- ⚠️ No rollback capability
- ⚠️ No validation of data integrity before deletion
- ⚠️ No file size limits
- ⚠️ No transaction logging
- ⚠️ No backup before deletion

---

## Security Requirements

### 1. Multi-Tenant Data Isolation

**Critical Requirements:**
- ✅ **MUST** enforce `customer_id` filtering at all layers
- ✅ **MUST** validate Customer ID in export file before import
- ✅ **MUST** prevent cross-tenant data leakage
- ✅ **MUST** log all export/import operations with customer_id

**Current Status:**
- ✅ Export filters by `customer_id` ✅
- ✅ Rehydration validates Customer ID match ✅
- ⚠️ Missing: Audit logging
- ⚠️ Missing: Access control checks

### 2. Data Protection

**Critical Requirements:**
- ⚠️ **SHOULD** encrypt exported files (especially for sensitive data)
- ⚠️ **SHOULD** implement file retention policies
- ⚠️ **SHOULD** add file size limits
- ⚠️ **SHOULD** implement rate limiting

**Current Status:**
- ❌ No file encryption
- ❌ No retention policies
- ❌ No file size limits
- ❌ No rate limiting

### 3. Audit & Compliance

**Critical Requirements:**
- ⚠️ **MUST** log all export operations (who, when, what)
- ⚠️ **MUST** log all import/rehydration operations (who, when, what, before/after counts)
- ⚠️ **SHOULD** track file access/downloads
- ⚠️ **SHOULD** maintain audit trail for compliance (GDPR, SOC 2, etc.)

**Current Status:**
- ❌ No export logging
- ❌ No import logging
- ❌ No audit trail

### 4. Data Integrity

**Critical Requirements:**
- ⚠️ **MUST** validate data before deletion (rehydration)
- ⚠️ **SHOULD** provide dry-run/preview mode
- ⚠️ **SHOULD** create backup before deletion
- ⚠️ **SHOULD** support rollback

**Current Status:**
- ❌ No validation before deletion
- ❌ No dry-run mode
- ❌ No backup before deletion
- ❌ No rollback capability

---

## Multi-Tenant Isolation Concerns

### Risk Assessment

| Risk | Severity | Current Mitigation | Gap |
|------|----------|-------------------|-----|
| Cross-tenant data export | 🔴 HIGH | `customer_id` filtering | ⚠️ No audit logging |
| Cross-tenant data import | 🔴 HIGH | Customer ID validation | ⚠️ No backup before deletion |
| Data corruption during import | 🟡 MEDIUM | Transaction rollback | ⚠️ No validation before deletion |
| Unauthorized access | 🟡 MEDIUM | Session-based auth | ⚠️ No access logging |
| File tampering | 🟡 MEDIUM | Customer ID in metadata | ⚠️ No file signature/encryption |

### Current Isolation Mechanisms

1. **Database-Level:**
   - All tables have `customer_id` foreign key
   - All queries filter by `customer_id`
   - ✅ **Working correctly**

2. **API-Level:**
   - `get_current_customer_id()` from session
   - Export filters by `customer_id`
   - Rehydration validates `customer_id` match
   - ✅ **Working correctly**

3. **File-Level:**
   - Export includes Customer ID in metadata
   - Rehydration validates Customer ID
   - ⚠️ **Needs enhancement:** File encryption, signature

---

## Export Feature Evaluation

### Strengths ✅

1. **Comprehensive Data Export:**
   - Exports all relevant data (13 sheets)
   - Includes metadata for rehydration
   - Includes Customer ID for validation

2. **Multi-Tenant Safe:**
   - Filters by `customer_id`
   - Includes Customer ID in export file

3. **Well-Structured:**
   - Organized into logical sheets
   - Includes headers and formatting

### Weaknesses ⚠️

1. **No Security:**
   - Files not encrypted
   - No access control beyond session
   - No audit logging

2. **No Limits:**
   - No file size limits
   - No rate limiting
   - No retention policies

3. **No Monitoring:**
   - No export tracking
   - No download tracking
   - No error monitoring

### Recommendations

1. **Add Audit Logging:**
   ```python
   # Log export operation
   ActivityLog.create(
       customer_id=customer_id,
       user_id=user_id,
       action='export_account_data',
       details={'file_size': file_size, 'accounts_count': len(accounts)}
   )
   ```

2. **Add File Encryption (Optional):**
   - Encrypt Excel file with customer-specific key
   - Store encryption key securely
   - Decrypt on import

3. **Add Rate Limiting:**
   - Limit exports per customer per day
   - Prevent abuse

4. **Add File Size Limits:**
   - Set maximum file size (e.g., 100MB)
   - Stream large files if needed

---

## Rehydration Feature Evaluation

### Strengths ✅

1. **Security Validation:**
   - Validates Customer ID match
   - Prevents cross-tenant imports
   - Validates export version

2. **Comprehensive Import:**
   - Imports all data types
   - Handles relationships (accounts → products → KPIs)
   - Preserves data integrity

3. **Error Handling:**
   - Transaction rollback on error
   - Error reporting per row
   - Continues processing on non-critical errors

### Weaknesses ⚠️

1. **Destructive Operation:**
   - **DELETES ALL DATA** before import
   - No backup before deletion
   - No rollback capability
   - No dry-run mode

2. **No Validation:**
   - Doesn't validate data integrity before deletion
   - Doesn't check if import will succeed
   - No preview of what will be imported

3. **No Recovery:**
   - If import fails, data is lost
   - No automatic backup
   - No restore capability

### Critical Risks

1. **Data Loss Risk:**
   - If import fails after deletion, all data is lost
   - No backup before deletion
   - No way to recover

2. **Data Corruption Risk:**
   - If file is corrupted, import may partially succeed
   - Partial data state is dangerous

3. **User Error Risk:**
   - User might import wrong file
   - No confirmation dialog
   - No preview

### Recommendations

1. **Add Backup Before Deletion:**
   ```python
   # Create backup before deletion
   backup_snapshot = create_account_snapshot(customer_id)
   # Then proceed with deletion
   ```

2. **Add Dry-Run Mode:**
   ```python
   # Preview what will be imported/deleted
   @rehydration_api.route('/api/rehydrate/preview', methods=['POST'])
   def preview_import():
       # Validate file, show what will be deleted/created
       # Don't actually delete/import
   ```

3. **Add Confirmation Step:**
   - Require explicit confirmation before deletion
   - Show summary of what will be deleted
   - Require user to type "DELETE" to confirm

4. **Add Validation Before Deletion:**
   - Validate file structure
   - Validate data integrity
   - Check for required sheets/columns
   - Only delete if validation passes

5. **Add Rollback Capability:**
   - Store backup before deletion
   - Allow rollback if import fails
   - Provide restore endpoint

---

## Vertical-Specific Considerations

### 1. Data Center / Serverless (Current Customer)

**Characteristics:**
- Regression-based health scores
- Product-level KPIs (Core Platform, Mobile App, etc.)
- KPI Reference Ranges (customer-specific)
- Historical data requirements

**Export Requirements:**
- ✅ Must export product-level KPIs
- ✅ Must export KPI Reference Ranges
- ✅ Must export health score calculation metadata

**Rehydration Requirements:**
- ✅ Must preserve product-level KPI relationships
- ✅ Must preserve KPI Reference Ranges
- ⚠️ **Question:** Should health scores be recalculated or preserved?

**Open Questions:**
1. Should health scores be recalculated on rehydration, or preserved from export?
2. How to handle missing historical data for regression formula?
3. Should KPI Reference Ranges be merged or replaced?

### 2. Marketplace / DCMarketPlace

**Characteristics:**
- Account-level KPIs (host quality, rentals, etc.)
- External account IDs
- Product usage tracking
- Support ticket data

**Export Requirements:**
- ✅ Must export external_account_id mappings
- ✅ Must export product usage data
- ✅ Must export support ticket history

**Rehydration Requirements:**
- ✅ Must preserve external_account_id mappings
- ⚠️ **Question:** How to handle account matching (by name or external_id)?

**Open Questions:**
1. Should accounts be matched by `external_account_id` or `account_name`?
2. How to handle duplicate accounts (same external_id, different names)?
3. Should we merge or replace existing accounts?

### 3. Corporate / Enterprise

**Characteristics:**
- Multiple accounts per customer
- Corporate-level rollups
- Complex profile_metadata
- Playbook executions

**Export Requirements:**
- ✅ Must export all accounts
- ✅ Must export playbook state
- ✅ Must export profile_metadata (JSON)

**Rehydration Requirements:**
- ✅ Must preserve account relationships
- ✅ Must preserve playbook state
- ⚠️ **Question:** Should playbook executions be resumed or reset?

**Open Questions:**
1. Should playbook executions be resumed from their previous state, or reset?
2. How to handle in-progress playbooks during rehydration?
3. Should we support partial rehydration (selective account import)?

### 4. Multi-Product Customers

**Characteristics:**
- Multiple products per account
- Product-level KPIs
- Product health scores
- Product-specific reference ranges

**Export Requirements:**
- ✅ Must export product-level KPIs
- ✅ Must export product relationships
- ✅ Must export product-specific configurations

**Rehydration Requirements:**
- ✅ Must preserve product-account relationships
- ✅ Must preserve product-level KPI relationships
- ⚠️ **Question:** How to handle orphaned products (account deleted but product exists)?

**Open Questions:**
1. How to handle orphaned products during rehydration?
2. Should we validate product-account relationships before import?
3. How to handle product name changes (same product_id, different name)?

---

## Open Questions

### General Questions

1. **Export Format:**
   - Should we support multiple export formats (Excel, CSV, JSON)?
   - Should we support incremental exports (only changed data)?
   - Should we support filtered exports (by date range, account, etc.)?

2. **Rehydration Mode:**
   - Should we support **MERGE** mode (update existing, add new) in addition to **REPLACE** mode?
   - Should we support **PARTIAL** rehydration (selective accounts/products)?
   - Should we support **DRY-RUN** mode (preview without changes)?

3. **Data Validation:**
   - What level of validation is required before import?
   - Should we validate data types, ranges, relationships?
   - Should we validate against schema/constraints?

4. **Error Handling:**
   - How to handle partial failures (some rows succeed, some fail)?
   - Should we continue processing on errors, or stop immediately?
   - How to report errors to user?

5. **Performance:**
   - What is the maximum file size we should support?
   - Should we support streaming for large files?
   - How to handle timeouts for large imports?

6. **Security:**
   - Should exported files be encrypted?
   - Should we require password for export/import?
   - Should we implement file signatures/checksums?

7. **Compliance:**
   - What audit logging is required for compliance (GDPR, SOC 2, etc.)?
   - How long should we retain export/import logs?
   - Should we support data retention policies?

### Vertical-Specific Questions

#### Data Center / Serverless

1. **Health Score Calculation:**
   - Should health scores be recalculated on rehydration, or preserved?
   - How to handle missing historical data for regression formula?
   - Should we validate health score formula compatibility?

2. **KPI Reference Ranges:**
   - Should KPI Reference Ranges be merged or replaced?
   - How to handle conflicts (same KPI name, different ranges)?
   - Should we validate range compatibility?

3. **Product-Level KPIs:**
   - How to handle product name changes?
   - How to handle product deletions?
   - Should we validate product-account relationships?

#### Marketplace / DCMarketPlace

1. **Account Matching:**
   - Should accounts be matched by `external_account_id` or `account_name`?
   - How to handle duplicate accounts (same external_id, different names)?
   - Should we merge or replace existing accounts?

2. **External IDs:**
   - How to handle missing external_account_id in export?
   - Should we generate new external_account_id if missing?
   - How to handle external_account_id conflicts?

#### Corporate / Enterprise

1. **Playbook State:**
   - Should playbook executions be resumed or reset?
   - How to handle in-progress playbooks during rehydration?
   - Should we support selective playbook import?

2. **Partial Rehydration:**
   - Should we support importing only selected accounts?
   - How to handle dependencies (products, KPIs) for partial import?
   - Should we support account-level rehydration?

---

## Recommendations

### Priority 1: Critical Security & Safety (Immediate)

1. **Add Backup Before Deletion:**
   - Create account snapshot before deletion
   - Store backup in database or file system
   - Allow restore if import fails

2. **Add Audit Logging:**
   - Log all export operations (who, when, what, file size)
   - Log all import operations (who, when, what, before/after counts)
   - Store logs in `activity_logs` table

3. **Add Validation Before Deletion:**
   - Validate file structure before deletion
   - Validate data integrity
   - Only delete if validation passes

4. **Add Confirmation Step:**
   - Require explicit confirmation before deletion
   - Show summary of what will be deleted
   - Require user to type "DELETE" to confirm

### Priority 2: User Experience (Short-term)

5. **Add Dry-Run Mode:**
   - Preview what will be imported/deleted
   - Show summary of changes
   - Don't actually delete/import

6. **Add Error Reporting:**
   - Detailed error messages per row
   - Summary of successes/failures
   - Downloadable error report

7. **Add Progress Tracking:**
   - Show progress bar during import
   - Show current step (validating, deleting, importing)
   - Allow cancellation

### Priority 3: Advanced Features (Medium-term)

8. **Add MERGE Mode:**
   - Update existing records, add new ones
   - Don't delete existing data
   - Handle conflicts intelligently

9. **Add Partial Rehydration:**
   - Import only selected accounts
   - Import only selected data types
   - Handle dependencies

10. **Add File Encryption:**
    - Encrypt exported files
    - Decrypt on import
    - Store encryption keys securely

### Priority 4: Performance & Scale (Long-term)

11. **Add Streaming Support:**
    - Stream large files
    - Process in chunks
    - Handle timeouts

12. **Add Rate Limiting:**
    - Limit exports per customer per day
    - Limit imports per customer per day
    - Prevent abuse

13. **Add File Size Limits:**
    - Set maximum file size (e.g., 100MB)
    - Warn users about large files
    - Provide alternatives for large exports

---

## Implementation Roadmap

### Phase 1: Security & Safety (Week 1-2)

- [ ] Add backup before deletion
- [ ] Add audit logging for exports
- [ ] Add audit logging for imports
- [ ] Add validation before deletion
- [ ] Add confirmation step

### Phase 2: User Experience (Week 3-4)

- [ ] Add dry-run/preview mode
- [ ] Add error reporting
- [ ] Add progress tracking
- [ ] Add cancellation support

### Phase 3: Advanced Features (Week 5-8)

- [ ] Add MERGE mode
- [ ] Add partial rehydration
- [ ] Add file encryption (optional)
- [ ] Add multiple export formats

### Phase 4: Performance & Scale (Week 9-12)

- [ ] Add streaming support
- [ ] Add rate limiting
- [ ] Add file size limits
- [ ] Add performance monitoring

---

## Conclusion

The current export and rehydration features are **functionally complete** but need **significant security and safety enhancements** before production use in a multi-tenant SaaS environment.

**Key Risks:**
1. 🔴 **Data Loss:** No backup before deletion
2. 🔴 **No Audit Trail:** No logging of export/import operations
3. 🟡 **No Validation:** No validation before destructive operations
4. 🟡 **No Recovery:** No rollback capability

**Recommended Next Steps:**
1. Implement Priority 1 items (backup, audit logging, validation, confirmation)
2. Test with different verticals (Data Center, Marketplace, Corporate)
3. Gather feedback from users
4. Implement Priority 2 items based on feedback

---

## Appendix: Code Examples

### Example: Backup Before Deletion

```python
# In rehydration_api.py
def import_account_data():
    customer_id = get_current_customer_id()
    
    # Create backup before deletion
    backup_snapshot = create_account_snapshot(customer_id)
    backup_id = backup_snapshot.snapshot_id
    
    try:
        # Proceed with deletion and import
        # ...
    except Exception as e:
        # Rollback to backup
        restore_from_snapshot(backup_id)
        raise
```

### Example: Audit Logging

```python
# In export_api.py
def export_all_account_data():
    customer_id = get_current_customer_id()
    user_id = get_current_user_id()
    
    # Log export operation
    ActivityLog.create(
        customer_id=customer_id,
        user_id=user_id,
        action='export_account_data',
        details={
            'file_size': file_size,
            'accounts_count': len(accounts),
            'kpis_count': len(kpis),
            'timestamp': datetime.now().isoformat()
        }
    )
    
    # Proceed with export
    # ...
```

### Example: Dry-Run Mode

```python
# In rehydration_api.py
@rehydration_api.route('/api/rehydrate/preview', methods=['POST'])
def preview_import():
    customer_id = get_current_customer_id()
    file = request.files.get('file')
    
    # Parse file
    xls = pd.ExcelFile(io.BytesIO(file.read()))
    
    # Count what will be deleted
    accounts_to_delete = Account.query.filter_by(customer_id=customer_id).count()
    kpis_to_delete = # ... count KPIs
    
    # Count what will be imported
    accounts_df = pd.read_excel(xls, sheet_name="Accounts Summary")
    accounts_to_import = len(accounts_df)
    
    # Return preview (don't actually delete/import)
    return jsonify({
        'preview': True,
        'will_delete': {
            'accounts': accounts_to_delete,
            'kpis': kpis_to_delete,
            # ...
        },
        'will_import': {
            'accounts': accounts_to_import,
            # ...
        }
    })
```

---

**Document Status:** Ready for Review  
**Next Steps:** Gather feedback, answer open questions, prioritize implementation

