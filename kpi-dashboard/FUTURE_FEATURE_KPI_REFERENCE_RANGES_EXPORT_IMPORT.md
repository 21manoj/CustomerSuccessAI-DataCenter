# Future Feature: KPI Reference Ranges Export/Import

**Status**: 🔮 Future Feature - TBD  
**Priority**: Medium  
**Phase**: Phase 2 (Months 4-6)  
**Requested By**: User on November 4, 2025  

---

## Overview

Add Excel/CSV export and import functionality for KPI Reference Ranges to enable bulk configuration management, backup/restore, and template sharing across customers.

## Business Value

### Benefits
- **Bulk Configuration**: Update multiple KPI ranges at once via Excel
- **Backup & Restore**: Export current configuration for backup purposes
- **Template Sharing**: Share reference range templates across customers or teams
- **Migration**: Easier migration between environments (dev → staging → production)
- **Audit & Compliance**: Export for audit trails and documentation
- **Offline Editing**: Edit ranges offline in familiar Excel interface

### Use Cases
1. **New Customer Onboarding**: Import industry-standard templates
2. **Configuration Management**: Backup before making changes
3. **Template Library**: Build library of templates for different industries
4. **Bulk Updates**: Update 68 ranges faster than clicking through UI
5. **Documentation**: Export for stakeholder review and approval

---

## Functional Requirements

### Export Functionality

#### Export Formats
- **Excel (.xlsx)**: Primary format with formatting and validation
- **CSV (.csv)**: Simple format for programmatic use

#### Export Options
1. **Export All Ranges** (System + Custom)
2. **Export System Defaults Only**
3. **Export Customer Overrides Only**
4. **Export Specific Categories** (filter by category)

#### Excel Export Structure
```
Sheet: KPI_Reference_Ranges
Columns:
- kpi_name (text)
- unit (text)
- higher_is_better (boolean: TRUE/FALSE)
- critical_min (number)
- critical_max (number)
- risk_min (number)
- risk_max (number)
- healthy_min (number)
- healthy_max (number)
- description (text, optional)
- is_custom (boolean: TRUE/FALSE, read-only)
- customer_id (number, read-only)
```

#### Data Validation (Excel)
- **higher_is_better**: Dropdown (TRUE, FALSE)
- **Numeric fields**: Data validation (numbers only)
- **Required fields**: Highlighted in yellow
- **Read-only fields**: Gray background

### Import Functionality

#### Import Sources
- **Excel (.xlsx)**: Parse and validate structure
- **CSV (.csv)**: Parse comma-delimited file

#### Import Modes
1. **Create New Overrides**: Create customer overrides for new KPIs
2. **Update Existing**: Update existing customer overrides
3. **Replace All**: Delete all customer overrides and import fresh (⚠️ dangerous)
4. **Merge**: Smart merge with conflict resolution

#### Validation Rules
- **Required fields**: kpi_name, unit, higher_is_better, all min/max values
- **Data types**: Validate numeric fields
- **Range logic**: Ensure min < max for each range
- **KPI name match**: Verify KPI exists in system defaults
- **Duplicate check**: No duplicate kpi_name per customer
- **Logical order**: Critical → Risk → Healthy makes sense

#### Error Handling
- **Validation errors**: Return list of errors with row numbers
- **Partial success**: Option to import valid rows, skip invalid
- **Rollback**: Transaction-based import (all or nothing)
- **Preview mode**: Show what will change before committing

---

## Technical Design

### API Endpoints

#### Export
```
GET /api/kpi-reference-ranges/export?format=xlsx&type=all
Headers: X-Customer-ID: <customer_id>
Response: File download (Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
```

Query Parameters:
- `format`: xlsx | csv
- `type`: all | system | custom | category
- `category`: (optional) filter by specific category

#### Import
```
POST /api/kpi-reference-ranges/import
Headers: 
  X-Customer-ID: <customer_id>
  Content-Type: multipart/form-data
Body: 
  file: <excel or csv file>
  mode: create | update | replace | merge
  preview: true | false (default: false)
  
Response (JSON):
{
  "status": "success",
  "preview": false,
  "imported": 15,
  "updated": 3,
  "skipped": 2,
  "errors": [
    {"row": 5, "error": "Invalid critical_min value"},
    {"row": 12, "error": "KPI name not found in system"}
  ],
  "summary": {
    "total_rows": 20,
    "valid_rows": 18,
    "invalid_rows": 2
  }
}
```

### Backend Implementation

#### Libraries
- **Export**: `openpyxl` (Python) or `pandas` for Excel generation
- **Import**: `openpyxl` or `pandas` for parsing
- **CSV**: Python built-in `csv` module

#### File Structure
```python
# backend/kpi_reference_ranges_export.py
def export_to_excel(customer_id, export_type='all'):
    """Export KPI ranges to Excel"""
    pass

def export_to_csv(customer_id, export_type='all'):
    """Export KPI ranges to CSV"""
    pass

# backend/kpi_reference_ranges_import.py
def import_from_excel(customer_id, file_path, mode='create', preview=False):
    """Import KPI ranges from Excel"""
    pass

def import_from_csv(customer_id, file_path, mode='create', preview=False):
    """Import KPI ranges from CSV"""
    pass

def validate_import_data(data):
    """Validate imported data structure and values"""
    pass
```

### Frontend Implementation

#### Settings UI Updates
```tsx
// Add to Settings.tsx
<div className="flex space-x-2">
  <button onClick={handleExport} className="...">
    📥 Export to Excel
  </button>
  <button onClick={handleImport} className="...">
    📤 Import from Excel
  </button>
</div>

// Export dropdown
<select onChange={handleExportType}>
  <option value="all">All Ranges</option>
  <option value="system">System Defaults Only</option>
  <option value="custom">My Custom Overrides</option>
</select>

// Import modal with file upload
<input type="file" accept=".xlsx,.csv" onChange={handleFileSelect} />
<select onChange={handleImportMode}>
  <option value="create">Create New Overrides</option>
  <option value="update">Update Existing</option>
  <option value="merge">Smart Merge</option>
</select>
<button onClick={handlePreview}>Preview Changes</button>
<button onClick={handleImportConfirm}>Import</button>
```

---

## Security Considerations

### Permissions
- ✅ Only customer can export their own overrides
- ✅ Only customer can import to their own account
- ✅ System defaults export available to all (read-only)
- ✅ System defaults import restricted to admins only

### Data Validation
- ✅ Sanitize all input data
- ✅ Validate file size limits (max 10MB)
- ✅ Check file type (only .xlsx, .csv)
- ✅ Prevent SQL injection via import data
- ✅ Rate limiting on import endpoint

### Audit Trail
- ✅ Log all exports (who, when, what)
- ✅ Log all imports (who, when, rows affected)
- ✅ Store imported file for audit purposes
- ✅ Track changes made via import

---

## Testing Requirements

### Unit Tests
- ✅ Export generation (Excel, CSV)
- ✅ Import parsing (valid files)
- ✅ Validation rules (all scenarios)
- ✅ Error handling (malformed files)
- ✅ Transaction rollback

### Integration Tests
- ✅ End-to-end export → import
- ✅ Multi-tenant isolation
- ✅ Copy-on-write behavior preserved
- ✅ System defaults not modified

### Manual Tests
- ✅ Export in Excel, edit, re-import
- ✅ Large file handling (68 KPIs × 1000 customers)
- ✅ UI flow (export/import buttons)
- ✅ Preview mode accuracy

---

## Documentation Requirements

### User Documentation
- **User Guide**: How to export/import KPI ranges
- **Video Tutorial**: Step-by-step walkthrough
- **Template Library**: Pre-built templates for industries
- **FAQ**: Common questions and troubleshooting

### Technical Documentation
- **API Documentation**: OpenAPI/Swagger specs
- **File Format Spec**: Excel/CSV structure
- **Integration Guide**: For programmatic import/export

---

## Implementation Estimate

### Effort
- **Backend (Export)**: 8 hours
- **Backend (Import)**: 16 hours (includes validation, error handling)
- **Frontend UI**: 8 hours
- **Testing**: 8 hours
- **Documentation**: 4 hours
- **Total**: ~44 hours (~1 week)

### Dependencies
- openpyxl library installation
- pandas library (optional, for advanced features)
- File storage for audit trail
- UI file upload component

---

## Related Features

### Templates Library (Future)
- Pre-built templates for industries (Healthcare, SaaS, Manufacturing)
- Community-contributed templates
- Template marketplace

### Version Control (Future)
- Track changes to reference ranges over time
- Rollback to previous configurations
- Diff view between versions

### Bulk Operations (Future)
- Bulk apply changes to multiple customers
- Template inheritance
- Global default updates

---

## Decision History

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-04 | Feature requested by user | User asked about export/import functionality |
| 2025-11-04 | Added to Phase 2 roadmap | Fits with "Advanced Analytics" and "Data Export" features |
| TBD | Priority to be determined | Pending customer feedback and demand |

---

## Notes

- This feature builds on the existing SaaS isolation work (customer_id in kpi_reference_ranges)
- Copy-on-write behavior must be preserved during import
- System defaults should be exportable but not importable (except by admins)
- Consider offering both "simple" and "advanced" import modes

---

**Last Updated**: November 4, 2025  
**Document Owner**: Product/Engineering Team

