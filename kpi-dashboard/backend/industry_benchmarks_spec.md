# Industry Benchmarks Data Format Specification

## Overview
Industry benchmarks provide percentile-based performance metrics for KPIs across different industries and company sizes. This enables customers to compare their performance against industry standards.

## Database Schema
```sql
CREATE TABLE industry_benchmarks (
    id INTEGER PRIMARY KEY,
    kpi_name VARCHAR(200) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    company_size VARCHAR(50),  -- startup, smb, enterprise
    percentile_25 FLOAT,
    percentile_50 FLOAT,  -- median
    percentile_75 FLOAT,
    percentile_90 FLOAT,
    sample_size INTEGER,
    data_source VARCHAR(200),
    last_updated DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Data Input Formats

### 1. CSV Format (Recommended for Bulk Import)
```csv
kpi_name,industry,company_size,percentile_25,percentile_50,percentile_75,percentile_90,sample_size,data_source,last_updated
Customer Satisfaction Score,Technology,startup,72.5,78.2,84.1,89.3,150,Industry Report 2024,2024-01-15
Customer Satisfaction Score,Technology,smb,68.1,75.8,82.4,87.9,300,Industry Report 2024,2024-01-15
Customer Satisfaction Score,Technology,enterprise,65.2,73.1,79.6,85.2,500,Industry Report 2024,2024-01-15
Net Promoter Score,Healthcare,startup,45.2,52.8,61.3,68.7,120,Healthcare Benchmark Study,2024-01-10
Net Promoter Score,Healthcare,smb,42.1,49.5,57.8,65.1,280,Healthcare Benchmark Study,2024-01-10
Net Promoter Score,Healthcare,enterprise,38.9,46.2,54.1,61.8,450,Healthcare Benchmark Study,2024-01-10
Monthly Recurring Revenue Growth,Technology,startup,8.5,12.3,18.7,25.4,200,VC Performance Report,2024-01-20
Monthly Recurring Revenue Growth,Technology,smb,5.2,8.9,14.1,20.3,350,VC Performance Report,2024-01-20
Monthly Recurring Revenue Growth,Technology,enterprise,3.1,6.7,11.2,16.8,400,VC Performance Report,2024-01-20
```

### 2. JSON Format (API Import)
```json
{
  "benchmarks": [
    {
      "kpi_name": "Customer Satisfaction Score",
      "industry": "Technology",
      "company_size": "startup",
      "percentile_25": 72.5,
      "percentile_50": 78.2,
      "percentile_75": 84.1,
      "percentile_90": 89.3,
      "sample_size": 150,
      "data_source": "Industry Report 2024",
      "last_updated": "2024-01-15"
    },
    {
      "kpi_name": "Net Promoter Score",
      "industry": "Healthcare",
      "company_size": "smb",
      "percentile_25": 42.1,
      "percentile_50": 49.5,
      "percentile_75": 57.8,
      "percentile_90": 65.1,
      "sample_size": 280,
      "data_source": "Healthcare Benchmark Study",
      "last_updated": "2024-01-10"
    }
  ]
}
```

### 3. Excel Format (Business User Friendly)
| KPI Name | Industry | Company Size | 25th %ile | 50th %ile | 75th %ile | 90th %ile | Sample Size | Data Source | Last Updated |
|----------|----------|--------------|-----------|-----------|-----------|-----------|-------------|-------------|--------------|
| Customer Satisfaction Score | Technology | startup | 72.5 | 78.2 | 84.1 | 89.3 | 150 | Industry Report 2024 | 2024-01-15 |
| Customer Satisfaction Score | Technology | smb | 68.1 | 75.8 | 82.4 | 87.9 | 300 | Industry Report 2024 | 2024-01-15 |
| Customer Satisfaction Score | Technology | enterprise | 65.2 | 73.1 | 79.6 | 85.2 | 500 | Industry Report 2024 | 2024-01-15 |

## Field Specifications

### Required Fields
- **kpi_name**: Exact KPI parameter name (must match existing KPIs)
- **industry**: Industry classification
- **percentile_50**: Median value (required)
- **sample_size**: Number of companies in sample (minimum 30)

### Optional Fields
- **company_size**: startup, smb, enterprise (if not specified, applies to all sizes)
- **percentile_25**: 25th percentile value
- **percentile_75**: 75th percentile value  
- **percentile_90**: 90th percentile value
- **data_source**: Source of benchmark data
- **last_updated**: When data was collected

### Industry Classifications
- Technology
- Healthcare
- Financial Services
- Manufacturing
- Retail
- Education
- Professional Services
- Government
- Non-Profit
- Other

### Company Size Classifications
- **startup**: < 50 employees, < $10M revenue
- **smb**: 50-500 employees, $10M-$100M revenue
- **enterprise**: > 500 employees, > $100M revenue

## Data Quality Requirements

### Sample Size Requirements
- Minimum 30 companies per benchmark
- Recommended 100+ companies for reliable percentiles
- Document sample size for transparency

### Data Freshness
- Update quarterly or annually
- Mark last_updated date
- Flag outdated benchmarks (> 2 years)

### Value Validation
- Percentiles must be in ascending order: 25th ≤ 50th ≤ 75th ≤ 90th
- Values must be realistic for KPI type
- Handle missing percentiles gracefully

## API Endpoints for Import

### Bulk Import CSV
```bash
POST /api/benchmarks/import-csv
Content-Type: multipart/form-data
X-Customer-ID: {customer_id}

file: benchmarks.csv
```

### Bulk Import JSON
```bash
POST /api/benchmarks/import-json
Content-Type: application/json
X-Customer-ID: {customer_id}

{
  "benchmarks": [...]
}
```

### Single Benchmark
```bash
POST /api/benchmarks
Content-Type: application/json
X-Customer-ID: {customer_id}

{
  "kpi_name": "Customer Satisfaction Score",
  "industry": "Technology",
  "company_size": "startup",
  "percentile_25": 72.5,
  "percentile_50": 78.2,
  "percentile_75": 84.1,
  "percentile_90": 89.3,
  "sample_size": 150,
  "data_source": "Industry Report 2024"
}
```

## Usage in RAG System

### Query Examples
- "How does our customer satisfaction compare to industry benchmarks?"
- "What are the typical NPS scores for technology startups?"
- "Show me revenue growth benchmarks for healthcare companies"

### Response Format
```json
{
  "kpi_name": "Customer Satisfaction Score",
  "customer_value": 76.5,
  "industry_benchmark": {
    "percentile_25": 72.5,
    "percentile_50": 78.2,
    "percentile_75": 84.1,
    "percentile_90": 89.3
  },
  "performance_level": "Below Median",
  "percentile_rank": 35,
  "recommendation": "Focus on improving customer support processes to reach median performance"
}
```

## Sample Data Sources

### Recommended Sources
1. **Industry Reports**: Gartner, Forrester, McKinsey
2. **Survey Data**: Customer Success Collective, Gainsight
3. **Public Data**: SEC filings, annual reports
4. **Partner Data**: Aggregated anonymized customer data
5. **Research Studies**: Academic papers, consulting reports

### Data Collection Strategy
1. **Primary Research**: Survey customers and partners
2. **Secondary Research**: Industry reports and studies
3. **Public Data**: SEC filings, earnings calls
4. **Partner Networks**: Data sharing agreements
5. **Crowdsourced**: Community contributions

## Implementation Priority

### Phase 1: Core KPIs (High Priority)
- Customer Satisfaction Score
- Net Promoter Score
- Customer Health Score
- Monthly Recurring Revenue Growth
- Customer Lifetime Value
- Churn Rate

### Phase 2: Industry-Specific KPIs
- Technology: Feature Adoption Rate, API Usage
- Healthcare: Patient Satisfaction, Readmission Rate
- Financial: Loan Approval Rate, Risk Score

### Phase 3: Advanced Metrics
- Predictive KPIs
- Leading indicators
- Composite scores
