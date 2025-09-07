# Data Format Specifications for RAG System

## Overview
This document provides detailed specifications for importing industry benchmarks and best practices content into the RAG system. Both data types are essential for providing contextual, actionable insights to customers.

## 📊 Industry Benchmarks Format

### Purpose
Industry benchmarks enable customers to compare their KPI performance against industry standards, providing context for improvement opportunities.

### Database Schema
```sql
CREATE TABLE industry_benchmarks (
    id INTEGER PRIMARY KEY,
    kpi_name VARCHAR(200) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    company_size VARCHAR(50),  -- startup, smb, enterprise
    percentile_25 FLOAT,
    percentile_50 FLOAT,  -- median (required)
    percentile_75 FLOAT,
    percentile_90 FLOAT,
    sample_size INTEGER,
    data_source VARCHAR(200),
    last_updated DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Supported Formats

#### 1. CSV Format (Recommended)
```csv
kpi_name,industry,company_size,percentile_25,percentile_50,percentile_75,percentile_90,sample_size,data_source,last_updated
Customer Satisfaction Score,Technology,startup,72.5,78.2,84.1,89.3,150,Industry Report 2024,2024-01-15
Customer Satisfaction Score,Technology,smb,68.1,75.8,82.4,87.9,300,Industry Report 2024,2024-01-15
```

#### 2. JSON Format
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
    }
  ]
}
```

#### 3. Excel Format
| KPI Name | Industry | Company Size | 25th %ile | 50th %ile | 75th %ile | 90th %ile | Sample Size | Data Source | Last Updated |
|----------|----------|--------------|-----------|-----------|-----------|-----------|-------------|-------------|--------------|
| Customer Satisfaction Score | Technology | startup | 72.5 | 78.2 | 84.1 | 89.3 | 150 | Industry Report 2024 | 2024-01-15 |

### Field Requirements

#### Required Fields
- **kpi_name**: Exact KPI parameter name (must match existing KPIs)
- **industry**: Industry classification
- **percentile_50**: Median value (required)
- **sample_size**: Number of companies in sample (minimum 30)

#### Optional Fields
- **company_size**: startup, smb, enterprise (if not specified, applies to all sizes)
- **percentile_25**: 25th percentile value
- **percentile_75**: 75th percentile value  
- **percentile_90**: 90th percentile value
- **data_source**: Source of benchmark data
- **last_updated**: When data was collected (YYYY-MM-DD format)

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

### Data Quality Requirements
- Sample size minimum: 30 companies
- Percentiles must be in ascending order: 25th ≤ 50th ≤ 75th ≤ 90th
- Values must be realistic for KPI type
- Update quarterly or annually

## 📚 Best Practices Content Library Format

### Purpose
Best practices provide actionable recommendations and implementation guidance for improving KPI performance.

### Database Schema
```sql
CREATE TABLE kpi_best_practices (
    id INTEGER PRIMARY KEY,
    kpi_name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    implementation_steps JSON,  -- Array of steps
    expected_impact TEXT,
    typical_improvement_percentage FLOAT,
    implementation_timeframe VARCHAR(50),  -- weeks, months
    difficulty_level VARCHAR(20),  -- low, medium, high
    cost_estimate VARCHAR(100),  -- low, medium, high, specific amount
    industry_applicability JSON,  -- Array of industries
    company_size_applicability JSON,  -- startup, smb, enterprise
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Supported Formats

#### 1. JSON Format (Recommended)
```json
{
  "best_practices": [
    {
      "kpi_name": "Customer Satisfaction Score",
      "category": "Customer Sentiment",
      "title": "Implement Proactive Customer Success Outreach",
      "description": "Establish a systematic approach to reaching out to customers before issues arise...",
      "implementation_steps": [
        "Identify at-risk customers using health score algorithms",
        "Create personalized outreach templates based on customer segment",
        "Schedule quarterly business reviews (QBRs) with key stakeholders"
      ],
      "expected_impact": "Proactive outreach typically increases customer satisfaction by 15-25%...",
      "typical_improvement_percentage": 20.0,
      "implementation_timeframe": "4-6 weeks",
      "difficulty_level": "medium",
      "cost_estimate": "medium",
      "industry_applicability": ["Technology", "Professional Services", "Healthcare"],
      "company_size_applicability": ["smb", "enterprise"]
    }
  ]
}
```

#### 2. CSV Format
```csv
kpi_name,category,title,description,implementation_steps,expected_impact,typical_improvement_percentage,implementation_timeframe,difficulty_level,cost_estimate,industry_applicability,company_size_applicability
Customer Satisfaction Score,Customer Sentiment,Implement Proactive Customer Success Outreach,"Establish a systematic approach...","[""Identify at-risk customers..."",""Create personalized outreach...""]","Proactive outreach typically increases...",20.0,4-6 weeks,medium,medium,"[""Technology"",""Professional Services""]","[""smb"",""enterprise""]"
```

### Field Requirements

#### Required Fields
- **kpi_name**: Exact KPI parameter name (must match existing KPIs)
- **category**: KPI category (Customer Sentiment, Product Usage, etc.)
- **title**: Descriptive title (max 300 characters)
- **description**: Detailed description of the best practice
- **implementation_steps**: Array of actionable steps

#### Optional Fields
- **expected_impact**: Description of expected results
- **typical_improvement_percentage**: Expected improvement (0-100%)
- **implementation_timeframe**: Duration to implement
- **difficulty_level**: low, medium, high
- **cost_estimate**: low, medium, high, or specific amount
- **industry_applicability**: Array of applicable industries
- **company_size_applicability**: Array of applicable company sizes

### Content Categories
- Customer Sentiment
- Product Usage
- Business Outcomes
- Relationship Strength
- Operational Excellence

### Implementation Steps Format
```json
[
  "Step 1: Brief description of action",
  "Step 2: Brief description of action",
  "Step 3: Brief description of action"
]
```

### Timeframe Options
- Immediate: < 1 week
- Quick: 1-2 weeks
- Short: 2-4 weeks
- Medium: 4-6 weeks
- Long: 6-12 weeks
- Extended: 3+ months

### Difficulty Levels
- **Low**: Basic implementation, minimal resources
- **Medium**: Moderate complexity, some expertise required
- **High**: Complex implementation, significant expertise required

### Cost Estimates
- **Low**: < $1,000
- **Medium**: $1,000 - $10,000
- **High**: $10,000 - $50,000
- **Enterprise**: $50,000+
- **Specific**: Exact dollar amount

## 🚀 Import Tools

### Industry Benchmarks Import
```bash
cd /Users/manojgupta/kpi-dashboard/backend
python3 import_benchmarks.py
```

### Best Practices Import
```bash
cd /Users/manojgupta/kpi-dashboard/backend
python3 import_best_practices.py
```

### API Endpoints

#### Import Benchmarks
```bash
POST /api/benchmarks/import-csv
Content-Type: multipart/form-data
X-Customer-ID: {customer_id}

file: benchmarks.csv
```

#### Import Best Practices
```bash
POST /api/best-practices/import-json
Content-Type: application/json
X-Customer-ID: {customer_id}

{
  "best_practices": [...]
}
```

## 📁 Sample Data Files

### Industry Benchmarks
- **File**: `sample_industry_benchmarks.csv`
- **Content**: 25 sample benchmarks across Technology, Healthcare, and Financial Services
- **KPIs**: Customer Satisfaction Score, Net Promoter Score, MRR Growth, Customer Health Score, Churn Rate, Feature Adoption Rate

### Best Practices
- **File**: `sample_best_practices.json`
- **Content**: 8 comprehensive best practices
- **KPIs**: Customer Satisfaction Score, Net Promoter Score, Customer Health Score, Feature Adoption Rate, MRR Growth, Churn Rate

## 🔍 Usage in RAG System

### Query Examples
- "How does our customer satisfaction compare to industry benchmarks?"
- "What are the best practices for improving NPS?"
- "Show me revenue growth benchmarks for technology startups"
- "What low-cost practices can improve customer health scores?"

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
  "recommended_practices": [
    {
      "title": "Implement Proactive Customer Success Outreach",
      "expected_improvement": "15-25%",
      "implementation_timeframe": "4-6 weeks",
      "difficulty_level": "medium",
      "cost_estimate": "medium"
    }
  ]
}
```

## 📋 Implementation Checklist

### Phase 1: Data Import
- [ ] Import sample industry benchmarks
- [ ] Import sample best practices
- [ ] Test import scripts with custom data
- [ ] Validate data quality and completeness

### Phase 2: RAG Integration
- [ ] Update RAG system to include benchmarks
- [ ] Update RAG system to include best practices
- [ ] Test query responses with new data
- [ ] Optimize search and retrieval

### Phase 3: Content Management
- [ ] Create content management interface
- [ ] Implement content review process
- [ ] Set up regular data updates
- [ ] Monitor usage and effectiveness

## 🎯 Success Metrics

### Industry Benchmarks
- Number of benchmarks imported
- Coverage across industries and KPIs
- Query response accuracy
- Customer engagement with benchmark data

### Best Practices
- Number of best practices available
- Implementation success rates
- Customer satisfaction with recommendations
- Measurable improvement in KPI performance

## 📞 Support

For questions about data formats or import issues:
1. Check the sample data files for format examples
2. Run the import scripts with verbose logging
3. Validate data against the schema requirements
4. Contact the development team for assistance
