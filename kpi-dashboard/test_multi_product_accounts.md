# Test Plan: Multi-Product Accounts KPI Display

## Test Accounts (Customer ID 1)
These accounts have multiple products and product-level KPIs:

1. **TechVision** (ID: 23)
   - Products: Core Platform, Mobile App, Analytics Dashboard
   - Product-level KPIs: 15 (5 per product)
   - Account-level KPIs: 59

2. **NetCore** (ID: 25)
   - Products: Mobile App, Integration Hub, API Gateway
   - Product-level KPIs: 15 (5 per product)
   - Account-level KPIs: 59

3. **NextGen Technologies** (ID: 53)
   - Products: Core Platform, Mobile App, API Gateway
   - Product-level KPIs: 15 (5 per product)
   - Account-level KPIs: 23

## Test Cases

### 1. Account Detail View
**Expected Behavior:**
- When viewing an account with multiple products, should show:
  - All product-level KPIs (grouped by product name)
  - Account-level KPIs (excluding parameters that have product-level KPIs, unless they're aggregates)
  - Product column should show product name for product-level KPIs
  - Product column should show "Account Level" for account-level KPIs

**Test Steps:**
1. Navigate to Account Health tab
2. Click on "TechVision" account
3. Verify:
   - KPI count shows: "Showing X KPIs (15 Product-level, Y Account-level)"
   - Table shows product-level KPIs with product names (Core Platform, Mobile App, Analytics Dashboard)
   - Table shows account-level KPIs with "Account Level" label
   - All 15 product-level KPIs are visible

### 2. Product Health Tab
**Expected Behavior:**
- Should show all products with their associated accounts
- Accounts with multiple products should appear in multiple product groups
- Only accounts that exist in the database should be shown
- Product-level KPIs should be counted correctly

**Test Steps:**
1. Navigate to Product Health tab
2. Verify:
   - "Core Platform" shows 12 accounts (including TechVision, NextGen Technologies, etc.)
   - "Mobile App" shows 12 accounts
   - "API Gateway" shows 11 accounts
   - "Integration Hub" shows 1 account (NetCore)
   - "Analytics Dashboard" shows 1 account (TechVision)
   - No accounts like DataPulse, CloudNexus, etc. are shown
   - Each product shows correct account count and revenue

### 3. Product Health Tab - Expand Product
**Expected Behavior:**
- When expanding a product, should show:
  - All accounts using that product
  - Product-level KPIs for that product
  - Account-level KPIs as fallback (if no product-level KPIs exist)

**Test Steps:**
1. Navigate to Product Health tab
2. Expand "Core Platform"
3. Verify:
   - Shows accounts like TechVision, NextGen Technologies, etc.
   - Shows product-level KPIs for Core Platform
   - Each KPI row shows the correct account name

## Verification Checklist

- [ ] Account detail view shows product-level KPIs for multi-product accounts
- [ ] Product Health tab shows correct account counts per product
- [ ] Product Health tab excludes non-existent accounts (DataPulse, CloudNexus, etc.)
- [ ] Product-level KPIs display with correct product names
- [ ] Account-level KPIs display with "Account Level" label
- [ ] KPI counts match database (15 product-level + account-level for TechVision)
- [ ] All 12 multi-product accounts appear correctly in Product Health tab



