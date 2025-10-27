# KPI Upload Format Guide

## ✅ Flexible Format Support

The KPI Dashboard V3 supports **multiple file formats** with automatic detection and adaptation.

## Supported Formats

### 1. **Standard Excel Format** (Current Default)
- **File**: Excel (.xlsx, .xls)
- **Sheets**: Multiple category sheets (e.g., "Product Usage", "Customer Sentiment")
- **Required Columns**:
  - `Health Score Component`
  - `KPI/Parameter`
  - `Data`
  - `Weight (%)`
- **Optional Columns**:
  - `Impact Level` (Critical, High, Medium, Low)
  - `Source Review`
  - `Measurement Frequency`

### 2. **Simple Excel Format**
- **File**: Excel (.xlsx, .xls)
- **Sheets**: Single "KPIs" sheet
- **Required Columns**:
  - `KPI Name`
  - `Value`
  - `Category`

### 3. **Custom Excel Format**
- **File**: Excel (.xlsx, .xls)
- **Sheets**: Flexible (detected automatically)
- **Required Columns**:
  - `KPI`
  - `Value`

### 4. **Basic CSV Format**
- **File**: CSV
- **Required Columns**:
  - `kpi_name`
  - `value`
  - `category`

### 5. **Standard CSV Format**
- **File**: CSV
- **Required Columns**:
  - `kpi_parameter`
  - `data`
  - `category`
  - `weight`

## How It Works

### Automatic Format Detection

When a client uploads a file:

1. **Detection Phase**:
   - System analyzes file structure
   - Checks for expected columns/sheets
   - Assigns confidence score (0-1)
   - Requires minimum 0.6 confidence

2. **Validation Phase**:
   - Validates required fields exist
   - Checks data types
   - Ensures minimum data rows

3. **Adaptation Phase**:
   - Converts detected format to standard format
   - Handles column name variations
   - Normalizes data types
   - Maps to database schema

### Column Name Flexibility

The system handles variations in column names:

**Weight Column**:
- `Weight (%)`
- `Weight`
- `weight`
- `WEIGHT`
- `WEIGHT (%)`

**Impact Level Column**:
- `Impact level`
- `Impact Level`
- `Impact`
- `impact level`
- `IMPACT LEVEL`

## For New Clients

### Option 1: Use Standard Format (Recommended)
- Download the template from the UI
- Fill in your KPI data
- Upload directly

### Option 2: Bring Your Own Format
Supported if you have:
- **Excel**: At minimum, columns for KPI name, value, and category
- **CSV**: At minimum, columns for kpi_name, value, and category

**Custom format requirements**:
- Must have KPI identification (name/parameter)
- Must have value (data/measurement)
- Must have category/classification
- Can have additional fields (impact, weight, etc.)

### Format Validation

The system will:
1. ✅ **Accept** if format is detected with high confidence
2. ⚠️ **Warn** but accept if format is detected with medium confidence
3. ❌ **Reject** if format cannot be detected or validated

## Example: Custom Format Support

### Client brings:
```csv
metric_name,score,category,priority
Customer Satisfaction,85.5,Sentiment,High
Product Usage,72.3,Product,Medium
```

### System detects:
- Format: `csv_basic` (confidence: 0.75)
- Maps: `metric_name` → `kpi_parameter`, `score` → `data`, `category` → `category`, `priority` → `impact_level`
- Result: ✅ **Accepted and processed**

## Upload APIs

### Basic Upload (`/api/upload`)
- Uses standard format only
- Strict validation
- No format detection

### Enhanced Upload (`/api/upload-enhanced`) ⭐ **Recommended**
- Automatic format detection
- Multiple format support
- Automatic RAG rebuild
- Better error messages

## Best Practices

1. **Use Enhanced Upload API** for maximum flexibility
2. **Provide sample file** before upload if using custom format
3. **Test with small file** before uploading full dataset
4. **Contact support** if your format isn't detected correctly

## Troubleshooting

### "Unsupported file format" Error
- Check file extension (.xlsx, .xls, .csv)
- Ensure minimum required columns exist
- Contact support with sample file

### "Format validation failed" Error
- Check data types (numbers should be numeric)
- Ensure no empty required fields
- Review error messages for specific issues

### "Low confidence detection" Warning
- File accepted but may have data quality issues
- Review suggested mapping carefully
- Contact support if mapping is incorrect

## References

- Sample files: `backend/sample_data/`
- Format specifications: `backend/DATA_FORMAT_SPECIFICATIONS.md`
- Detection logic: `backend/format_detection.py`
- Adapter implementations: `backend/format_adapters.py`

## Summary

✅ **Clients CAN bring their own schema** if it has minimum required fields  
✅ **Automatic format detection** handles variations  
✅ **Multiple format support** (Excel, CSV, various structures)  
✅ **Flexible column mapping** handles naming variations  
⚠️ **Minimum requirements**: KPI name, value, and category  

**For custom formats, use the Enhanced Upload API for best results!**
