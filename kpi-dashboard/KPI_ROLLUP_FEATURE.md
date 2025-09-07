# KPI Rollup Feature

## Overview

The KPI Rollup feature provides a simulation-based two-level scoring system that calculates weighted rollup scores across KPI categories and determines overall maturity tiers. This is implemented as a **simulation-only feature** with rollback capability to ensure data integrity.

## How It Works

### Two-Level Rollup Calculation

1. **Category-Level Rollup**: Within each category, KPIs are scored using:
   - Normalized weights (sum to 100% within category)
   - KPI data values (actual or sample data)
   - Formula: `Category Score = Σ(KPI_weight × KPI_data_value)`

2. **Overall Rollup**: Across categories, scores are combined using:
   - Predefined category weights
   - Formula: `Overall Score = Σ(category_score × category_weight)`

### Category Weights

The system uses predefined category weights:
- **Product Usage KPI**: 25%
- **Customer Success KPI**: 25%
- **Business Outcomes KPI**: 30%
- **Relationship Strength KPI**: 20%

### Maturity Tiers

Based on the overall score:
- **Healthy**: ≥75 points
- **At Risk**: 50-74 points
- **Critical**: <50 points

## Features

### Simulation Mode
- All calculations are performed in memory
- No permanent changes to KPI data
- Results are for demonstration purposes only

### Sample Data Generation
- Automatically generates sample data for KPIs without data values
- Random scores between 30-90 for demonstration
- Clear notification when sample data is used

### Rollback Functionality
- "Rollback" button returns to original state
- Refreshes KPI data from the server
- Ensures no permanent changes are made

### Visual Indicators
- Color-coded maturity tiers (Green/Yellow/Red)
- Progress bars for category scores
- Detailed breakdown of calculations

## Usage

1. **Navigate to KPI Rollup Tab**: Click the "KPI Rollup" tab in the dashboard
2. **Run Simulation**: Click "Run Simulation" to calculate scores
3. **Review Results**: 
   - Overall score and maturity tier
   - Category breakdown with individual scores
   - Recommendations based on performance
4. **Rollback**: Click "Rollback" to return to original state

## Technical Implementation

### Frontend Components
- `KPIRollup.tsx`: Main simulation component
- Integrated into `Dashboard.tsx` as a new tab
- TypeScript interfaces for type safety

### Key Functions
- `parseNumericValue()`: Handles various data formats
- `normalizeWeights()`: Normalizes KPI weights within categories
- `calculateCategoryScore()`: Computes weighted category scores
- `getMaturityTier()`: Determines maturity level
- `generateSampleData()`: Creates demo data for empty fields

### Data Flow
1. KPI data loaded from backend
2. Sample data generated for empty fields (if needed)
3. Weights normalized within categories
4. Category scores calculated
5. Overall score computed using category weights
6. Maturity tier and recommendations generated
7. Results displayed with rollback option

## Future Enhancements

- **Configurable Category Weights**: Allow users to adjust category weights
- **Custom Maturity Thresholds**: User-defined tier boundaries
- **Historical Tracking**: Save simulation results for comparison
- **Export Results**: Generate reports from simulation data
- **Real Data Integration**: Connect to actual KPI data sources

## Notes

- This is a **simulation feature** - no data is permanently modified
- Sample data is generated for demonstration purposes
- All calculations are performed client-side for performance
- The feature helps understand how KPI rollup scoring would work in practice 