# Product Analytics Implementation Guide

## Overview
Complete product-level analytics system with master product catalog, health score tracking, and aggregate trends.

## Architecture

### Tables Created
1. **`product_catalog`** - Master normalized product catalog
2. **`product_trends`** - Per-account product health trends (monthly)
3. **`product_aggregate_trends`** - Aggregate product health across all accounts

### Key Components

#### 1. Product Normalization (`product_normalization.py`)
- Extracts products from `account.profile_metadata.products_used`
- Normalizes product names (handles typos, case differences)
- Uses similarity search (Levenshtein distance) to match existing products
- Creates new catalog entries when needed
- **Future**: Product catalog will be starting point, metadata will link to it

#### 2. Health Score Calculator (`product_health_calculator.py`)
- Calculates product health from:
  - Product-level KPIs (KPIs with `product_id` set)
  - Account-level KPIs from "Product Usage KPI" and "Support KPI" pillars
- Stores in `product_trends` (per account-product)
- Calculates aggregate trends across all accounts
- Stores in `product_aggregate_trends`

#### 3. Event Subscriber (`product_health_subscriber.py`)
- Automatically triggers on:
  - KPI data upload
  - Account data changes
  - Health score updates
- Calculates product health with cooldown (1 minute) to avoid excessive calculations

#### 4. API Endpoints (`product_analytics_api.py`)
- `GET /api/products/health` - Get product health scores
- `GET /api/products/catalog` - Get product catalog
- `POST /api/products/recalculate` - Manually recalculate product health

## Setup Steps

### 1. Create Database Tables
```bash
cd kpi-dashboard/backend
python3 create_product_analytics_tables.py
```

### 2. Register Models in `models.py`
Add to imports:
```python
from product_analytics_models import ProductCatalog, ProductTrend, ProductAggregateTrend
```

### 3. Register API in `app_v3_minimal.py`
Add to imports:
```python
from product_analytics_api import product_analytics_api
```

Register blueprint:
```python
app.register_blueprint(product_analytics_api)
```

### 4. Register Event Subscriber in `event_system.py`
Add to subscribers:
```python
from product_health_subscriber import ProductHealthSubscriber
event_manager.subscribe(ProductHealthSubscriber())
```

## Data Flow

### On KPI Upload:
```
1. KPI Upload Event → ProductHealthSubscriber
2. Extract products from account metadata
3. Normalize and link to product_catalog
4. Calculate health scores from KPIs
5. Store in product_trends (per account-product)
6. Calculate aggregate trends → product_aggregate_trends
```

### On Manual Recalculation:
```
POST /api/products/recalculate
→ calculate_and_store_product_health()
→ Same flow as above
```

## Usage Examples

### Get Product Health for Customer
```bash
GET /api/products/health?aggregate=true
Headers: X-Customer-ID: 1
```

### Get Product Health for Specific Account
```bash
GET /api/products/health?account_id=334
Headers: X-Customer-ID: 1
```

### Get Product Catalog
```bash
GET /api/products/catalog
Headers: X-Customer-ID: 1
```

### Recalculate Product Health
```bash
POST /api/products/recalculate
Headers: X-Customer-ID: 1
Body: { "account_id": 334 }  # Optional, empty for all accounts
```

## Integration with Frontend

The Product Health Dashboard can now query:
- `/api/products/health?aggregate=true` - For aggregate product health
- `/api/products/health?account_id=X` - For account-specific product health
- `/api/products/catalog` - For product list

## Future Enhancements

1. **Product-level KPIs as primary source**: Currently uses account-level KPIs as fallback
2. **Product catalog as starting point**: Metadata will link to catalog entries
3. **Product-level playbooks**: Recommendations based on product health
4. **Product adoption trends**: Track product adoption over time
5. **Product forecasting**: Predict product health trends

## Notes

- Product names are normalized per customer (same name can exist for different customers)
- Similarity threshold: 0.85 (configurable in `find_or_create_product()`)
- Health scores calculated monthly (like `health_trends`)
- Aggregate trends weighted by revenue
- Cooldown: 1 minute between calculations for same account
