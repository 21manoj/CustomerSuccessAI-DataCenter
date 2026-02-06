# DC2_S KPI Configuration User Guide

## Overview

The DC2_S platform allows you to customize your health scoring model by configuring:
- **Pillar Weights**: How much each pillar contributes to overall health
- **KPI Selection**: Which KPIs to track (from catalog or custom)
- **KPI Weights**: How much each KPI contributes to its pillar
- **Custom KPIs**: Define your own KPIs with custom targets and ranges

---

## Accessing Settings

1. Navigate to `/dc-dashboard/settings`
2. Click on the **"General Configuration"** tab
3. You'll see the KPI Configuration Settings interface

---

## Configuring Pillar Weights

### Step 1: Navigate to Pillar Weights Tab

1. Click on **"1. Pillar Weights"** tab
2. You'll see 5 pillars with sliders:
   - 🖥️ **AI Workload Performance** (default: 25%)
   - ❤️ **Customer Health** (default: 20%)
   - 🚀 **Deployment Velocity** (default: 15%)
   - 📈 **Expansion & Growth** (default: 20%)
   - 🛡️ **Operational Stability** (default: 20%)

### Step 2: Adjust Weights

1. Use the sliders to adjust each pillar's weight
2. **Important**: Weights must sum to exactly 100%
3. The total is displayed at the bottom (green = valid, red = invalid)

### Step 3: Save Changes

1. Click **"Save Changes"** button (appears when you have unsaved changes)
2. Changes are saved to your customer configuration

---

## Selecting KPIs

### Step 1: Navigate to KPI Selection Tab

1. Click on **"2. Select KPIs"** tab
2. You'll see 5 expandable pillar sections

### Step 2: Enable/Disable KPIs

1. Click on a pillar section to expand it
2. Check/uncheck KPIs to enable/disable them
3. You'll see:
   - **Catalog KPIs**: Pre-defined KPIs from the system
   - **Custom KPIs**: KPIs you've created (marked with "Custom" badge)

### Step 3: Add Custom KPI

1. Click **"+ Add Custom KPI to [Pillar]"** button
2. Fill out the form:
   - **KPI Code**: Must start with `CUSTOM-` (e.g., `CUSTOM-GPU-TEMP`)
   - **Pillar**: Select which pillar this KPI belongs to
   - **Display Name**: Human-readable name
   - **Description**: Optional description
   - **Unit**: Select unit (%, °C, watts, etc.)
   - **Target Value**: The ideal value
   - **Operator**: How to compare (>, <, =, >=, <=)
   - **Acceptable Range**: Min and max values
3. Click **"Save Custom KPI"**

### Step 4: Edit/Delete Custom KPIs

1. Find your custom KPI in the list
2. Click **"Edit"** to modify it
3. Click **"Delete"** to remove it (requires confirmation)

---

## Understanding KPI Definitions

### KPI Code Format

- **Catalog KPIs**: `AI-KPI1`, `CH-KPI4`, `DV-KPI2`, etc.
- **Custom KPIs**: `CUSTOM-*` (e.g., `CUSTOM-GPU-TEMP`)

### Target and Range

- **Target**: The ideal value for this KPI
- **Range**: Acceptable min/max values
- **Operator**: How to compare actual vs target
  - `>`: Higher is better (e.g., GPU utilization)
  - `<`: Lower is better (e.g., latency)
  - `=`: Exact match (e.g., configuration status)

### Score Calculation

The system calculates a score (0-100) based on:
- How close the actual value is to the target
- Whether it's within the acceptable range
- The operator type (>, <, =)

---

## API Usage

### Get Configuration

```bash
curl -X GET http://localhost:5059/api/dc2s/config/ \
  -H "Cookie: session=YOUR_SESSION"
```

### Update Pillar Weights

```bash
curl -X PUT http://localhost:5059/api/dc2s/config/pillar-weights \
  -H "Cookie: session=YOUR_SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "pillar_weights": {
      "AI": 0.30,
      "CH": 0.20,
      "DV": 0.15,
      "EX": 0.20,
      "OS": 0.15
    }
  }'
```

### Add Custom KPI

```bash
curl -X POST http://localhost:5059/api/dc2s/config/custom-kpi \
  -H "Cookie: session=YOUR_SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "kpi_code": "CUSTOM-GPU-TEMP",
    "kpi_definition": {
      "pillar": "AI",
      "name": "GPU Temperature",
      "description": "Average GPU temperature",
      "unit": "°C",
      "target": 75.0,
      "operator": "<",
      "range": [60, 85]
    }
  }'
```

### Calculate Scores

```bash
curl -X POST http://localhost:5059/api/dc2s/scores/calculate \
  -H "Cookie: session=YOUR_SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "measurement_month": "2024-12-01"
  }'
```

---

## Best Practices

1. **Start with Defaults**: Use default pillar weights initially, then adjust based on your business priorities

2. **Enable Relevant KPIs**: Only enable KPIs that you actually measure and track

3. **Custom KPIs**: Use custom KPIs for metrics specific to your infrastructure

4. **Regular Review**: Review and adjust weights quarterly based on business outcomes

5. **Test Changes**: After making changes, run score calculation to verify results

---

## Troubleshooting

### Weights Don't Sum to 100%

- Check the total at the bottom of the pillar weights section
- Adjust sliders until total = 100%
- System will not save if total ≠ 100%

### Custom KPI Not Appearing

- Verify KPI code starts with `CUSTOM-`
- Check that it's enabled in the KPI selection tab
- Ensure it belongs to the correct pillar

### Scores Not Calculating

- Verify you have KPI measurements in the database
- Check that enabled KPIs have data
- Ensure measurement month has data

---

## Support

For issues or questions:
- Check API documentation: `/api/dc2s/config/`
- Review error messages in browser console
- Contact your system administrator
