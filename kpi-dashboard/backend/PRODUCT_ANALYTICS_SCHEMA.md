# Product Analytics Database Schema

## Overview
Product-level analytics system with master product catalog, per-account product trends, and aggregate product trends.

## Tables

### 1. `product_catalog` - Master Product Catalog
**Purpose**: Normalized master table for all products across all customers/accounts. Handles product name normalization and deduplication.

```sql
CREATE TABLE product_catalog (
    product_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    product_name VARCHAR(255) NOT NULL,  -- Normalized/canonical name
    product_sku VARCHAR(100),
    product_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure unique product name per customer (normalized)
    UNIQUE(customer_id, product_name)
);

CREATE INDEX idx_product_catalog_customer ON product_catalog(customer_id);
CREATE INDEX idx_product_catalog_name ON product_catalog(product_name);
```

**Key Features**:
- `product_id` is the master reference (used everywhere)
- `product_name` stored here to avoid mismatch from metadata
- Normalized per customer (same product name can exist for different customers)
- Future: This will be the starting point, metadata will link to this

### 2. `product_trends` - Per-Account Product Health Trends
**Purpose**: Track product health scores over time for each account-product combination (similar to `health_trends` for accounts).

```sql
CREATE TABLE product_trends (
    trend_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES product_catalog(product_id),
    account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
    year INTEGER NOT NULL,
    
    -- Health Scores (0.00-100.00)
    overall_health_score NUMERIC(5, 2) NOT NULL,
    product_usage_score NUMERIC(5, 2),
    support_score NUMERIC(5, 2),
    customer_sentiment_score NUMERIC(5, 2),
    business_outcomes_score NUMERIC(5, 2),
    relationship_strength_score NUMERIC(5, 2),
    
    -- KPI Statistics
    total_kpis INTEGER DEFAULT 0,
    valid_kpis INTEGER DEFAULT 0,
    product_level_kpis INTEGER DEFAULT 0,  -- KPIs with product_id set
    account_level_kpis INTEGER DEFAULT 0,   -- Account-level KPIs used for this product
    
    -- Revenue (from account at time of calculation)
    revenue NUMERIC(15, 2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure unique combination of product, account, month, and year
    UNIQUE(product_id, account_id, month, year)
);

CREATE INDEX idx_product_trend_product_date ON product_trends(product_id, year, month);
CREATE INDEX idx_product_trend_account_date ON product_trends(account_id, year, month);
CREATE INDEX idx_product_trend_customer_date ON product_trends(customer_id, year, month);
CREATE INDEX idx_product_trend_product_account ON product_trends(product_id, account_id);
```

**Key Features**:
- Links to `product_catalog.product_id` (normalized reference)
- Tracks health scores per account-product combination
- Stores both product-level and account-level KPI counts
- Monthly tracking (like `health_trends`)

### 3. `product_aggregate_trends` - Aggregate Product Health Across Accounts
**Purpose**: Track aggregate product health across all accounts using that product (for revenue trends and portfolio view).

```sql
CREATE TABLE product_aggregate_trends (
    aggregate_trend_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES product_catalog(product_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
    year INTEGER NOT NULL,
    
    -- Aggregate Health Scores (weighted average across accounts)
    overall_health_score NUMERIC(5, 2) NOT NULL,
    product_usage_score NUMERIC(5, 2),
    support_score NUMERIC(5, 2),
    customer_sentiment_score NUMERIC(5, 2),
    business_outcomes_score NUMERIC(5, 2),
    relationship_strength_score NUMERIC(5, 2),
    
    -- Aggregate Statistics
    total_accounts INTEGER DEFAULT 0,  -- Number of accounts using this product
    total_revenue NUMERIC(15, 2),       -- Sum of revenue from all accounts
    average_revenue_per_account NUMERIC(15, 2),
    total_kpis INTEGER DEFAULT 0,
    valid_kpis INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure unique combination of product, month, and year
    UNIQUE(product_id, month, year)
);

CREATE INDEX idx_product_aggregate_product_date ON product_aggregate_trends(product_id, year, month);
CREATE INDEX idx_product_aggregate_customer_date ON product_aggregate_trends(customer_id, year, month);
```

**Key Features**:
- Aggregate view across all accounts using the product
- Weighted averages for health scores (by revenue or account count)
- Total revenue tracking for product portfolio analysis
- Monthly tracking

## Data Flow

### 1. Product Normalization (On Upload/Data Change)
```
Account.profile_metadata.products_used (comma-separated)
    ↓
Extract product names
    ↓
Similarity search against product_catalog
    ↓
Match existing OR create new product_catalog entry
    ↓
Link account to product via product_trends
```

### 2. Health Score Calculation (On Upload/Data Change)
```
KPI Upload/Change Event
    ↓
For each account:
    Extract products (from metadata or Product table)
    ↓
For each product:
    Calculate health scores from:
        - Product-level KPIs (product_id matches)
        - Account-level KPIs from Product Usage & Support pillars
    ↓
Store in product_trends (per account-product)
    ↓
Aggregate across accounts → product_aggregate_trends
```

### 3. Similarity Search Algorithm
- Normalize: lowercase, trim, remove special chars
- Exact match first
- Levenshtein distance for typos (threshold: 0.85)
- Substring matching for variations
- Manual resolution for conflicts

## Integration Points

### Upload Trigger
- `upload_api.py` / `enhanced_upload_api.py`
- After KPI upload → trigger product health calculation
- Extract products from account metadata
- Normalize and link to product_catalog
- Calculate and store product_trends

### Recalculation Trigger
- On KPI data change (edit, delete)
- On account metadata change (products_used updated)
- On manual recalculation request
- Event system integration (similar to AccountSnapshotSubscriber)

## Future Enhancements
- Product-level KPIs will be primary source (currently using account-level as fallback)
- Product catalog will be starting point (metadata will link to it)
- Product-level playbooks and recommendations
- Product adoption trends and forecasting
