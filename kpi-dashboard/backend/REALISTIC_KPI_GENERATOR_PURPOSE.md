# Realistic KPI Generator - Purpose and Usage

## Overview

`realistic_kpi_generator.py` is a service module located in `backend/verticals/_template/services/` that generates realistic KPI values with industry-standard units, ensuring consistency between test data and production data formats.

## Purpose

### Primary Purpose
**Generate KPIs with industry-standard units matching the Import Adapter, ensuring Journey Generator V2 speaks the SAME LANGUAGE as production data.**

### Key Functions

1. **Realistic Value Generation**
   - Generates KPI values in **raw units** (e.g., hours, percentage, count)
   - Uses predefined value ranges for different scenarios (healthy, at_risk, crisis, recovery)
   - Ensures values match production data formats

2. **Normalization**
   - Converts raw values to normalized scores (0-100 scale)
   - Uses `kpi_normalization_service` for proper unit conversion
   - Maintains consistency with production normalization logic

3. **Sparse KPI Handling**
   - Simulates real-world scenarios where not all KPIs are available
   - Uses `sparse_kpi_handler` to select which KPIs to include
   - Supports different patterns: 'typical', 'sparse', 'comprehensive'

4. **Scenario-Based Generation**
   - **healthy**: High values, optimal performance
   - **at_risk**: Moderate values, warning signs
   - **crisis**: Low values, critical issues
   - **recovery**: Improving values, post-crisis

## Who Calls It?

### 1. **Integration Tests** (Primary Usage)
   - `tests/integration/test_e2e_integration.py`
   - `tests/integration/test_integration.py`

   **Usage Example:**
   ```python
   from realistic_kpi_generator import RealisticKPIGenerator, CoverageLevel, PatternType
   
   generator = RealisticKPIGenerator()
   
   # Generate healthy KPIs
   healthy_kpis = generator.generate(
       pattern='typical',
       scenario='healthy'
   )
   
   # Verify health scores
   avg_score = sum(healthy_kpis.normalized_kpis.values()) / len(healthy_kpis.normalized_kpis)
   assert avg_score > 70, "Healthy pattern should have high scores"
   ```

### 2. **Test Scenarios**
   - Health calculation accuracy tests
   - Data quality verification
   - Coverage percentage validation
   - Pillar coverage checks

## Dependencies

### Required Services
1. **`kpi_normalization_service`**
   - Provides KPI definitions
   - Handles normalization/denormalization
   - Manages unit conversions

2. **`sparse_kpi_handler`**
   - Selects which KPIs to include based on pattern
   - Handles sparse data scenarios
   - Manages coverage levels

## Output Structure

```python
@dataclass
class RealisticKPIOutput:
    raw_kpis: Dict[str, Tuple[float, str]]    # {code: (value, unit)}
    normalized_kpis: Dict[str, float]          # {code: score 0-100}
    coverage_pct: float                        # Percentage of KPIs available
    data_quality: float                       # Quality score (0-1)
    missing_kpis: List[str]                   # KPIs not included
    available_kpis: List[str]                 # KPIs included
    pillar_coverage: Dict[str, float]        # Coverage per pillar
```

## Example Value Ranges

The generator uses predefined ranges for specific KPIs:

```python
value_ranges = {
    'mtbf': {
        'healthy': (10000, 15000),
        'at_risk': (6000, 10000),
        'crisis': (3000, 6000),
        'recovery': (7000, 11000)
    },
    'uptime_percentage': {
        'healthy': (99.5, 99.99),
        'at_risk': (99.0, 99.5),
        'crisis': (95, 99.0),
        'recovery': (99.2, 99.7)
    },
    'gpu_utilization_rate': {
        'healthy': (70, 90),
        'at_risk': (50, 70),
        'crisis': (30, 50),
        'recovery': (55, 75)
    },
    # ... more KPIs
}
```

## Why It Matters

### 1. **Consistency with Production**
   - Ensures test data matches production data formats
   - Uses same normalization logic as production
   - Maintains unit consistency

### 2. **Realistic Testing**
   - Simulates real-world sparse KPI scenarios
   - Tests different health states (healthy, at_risk, crisis, recovery)
   - Validates health score calculations

### 3. **Journey Generator Compatibility**
   - Ensures Wizard A (Journey Generator V2) receives data in expected format
   - Matches the language/format of production Excel imports
   - Supports accurate journey narrative generation

## Current Status

- ✅ **Used in**: Integration tests across all customer directories
- ✅ **Purpose**: Generate realistic test data for health calculations
- ❌ **NOT used in**: Production data generation (CSV seed files)
- ❌ **NOT used in**: Onboarding wizard sample file generation

## Potential Integration Points

### 1. **Onboarding Wizard Sample Generation**
   - Could replace hardcoded KPI generation in `generate_customer17_seed_data.py`
   - Would ensure generated CSVs match production format
   - Would use proper normalization and units

### 2. **Journey Generator V2**
   - Already designed to work with this format
   - Ensures consistent data structure
   - Supports accurate health score calculations

### 3. **Excel Import Service**
   - Could use for generating test Excel files
   - Ensures consistency with production imports
   - Validates import adapter compatibility

## Key Takeaway

`realistic_kpi_generator.py` is **primarily a testing utility** that ensures:
- Test data matches production data formats
- Health calculations are accurate
- Journey Generator receives properly formatted data

It's **not currently used** for generating seed CSV files in the onboarding wizard, but it **could be** to ensure consistency with production data formats.
