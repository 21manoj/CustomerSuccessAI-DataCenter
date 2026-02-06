# DC2_S Configuration & Scores API Documentation

## Base URL

```
http://localhost:5059
```

**Production:** Replace with your production URL

---

## Authentication

All endpoints require authentication via session cookie. Login first:

```bash
curl -X POST http://localhost:5059/api/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}' \
  -c cookies.txt
```

Then use the session cookie for subsequent requests:

```bash
curl -X GET http://localhost:5059/api/dc2s/config/ \
  -b cookies.txt
```

---

## Configuration API

### GET /api/dc2s/config/

Get current customer configuration.

**Response:**
```json
{
  "customer_id": 9,
  "is_default": false,
  "pillar_weights": {
    "AI": 0.25,
    "CH": 0.20,
    "DV": 0.15,
    "EX": 0.20,
    "OS": 0.20
  },
  "enabled_kpis": ["AI-KPI1", "CH-KPI4", ...],
  "kpi_definitions": {
    "CUSTOM-GPU-TEMP": {
      "pillar": "AI",
      "name": "GPU Temperature",
      "target": 75.0,
      "operator": "<",
      "range": [60, 85],
      "unit": "°C"
    }
  },
  "kpi_overrides": {},
  "kpi_weights": {
    "AI": {
      "AI-KPI1": 0.4,
      "AI-KPI2": 0.3,
      "CUSTOM-GPU-TEMP": 0.3
    }
  },
  "updated_at": "2026-01-23T13:00:00"
}
```

---

### PUT /api/dc2s/config/

Update customer configuration.

**Request Body:**
```json
{
  "pillar_weights": {
    "AI": 0.30,
    "CH": 0.20,
    "DV": 0.15,
    "EX": 0.20,
    "OS": 0.15
  },
  "enabled_kpis": ["AI-KPI1", "CH-KPI4", ...]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration updated"
}
```

**Errors:**
- `400`: Invalid input (e.g., weights don't sum to 100%)
- `401`: Not authenticated
- `500`: Server error

---

### PUT /api/dc2s/config/pillar-weights

Update pillar weights only.

**Request Body:**
```json
{
  "pillar_weights": {
    "AI": 0.30,
    "CH": 0.20,
    "DV": 0.15,
    "EX": 0.20,
    "OS": 0.15
  }
}
```

**Validation:**
- Weights must sum to exactly 1.0 (100%)
- Each weight must be between 0.1 and 0.4 (10% - 40%)

---

### POST /api/dc2s/config/custom-kpi

Add a custom KPI.

**Request Body:**
```json
{
  "kpi_code": "CUSTOM-GPU-TEMP",
  "kpi_definition": {
    "pillar": "AI",
    "name": "GPU Temperature",
    "description": "Average GPU temperature across all nodes",
    "unit": "°C",
    "target": 75.0,
    "operator": "<",
    "range": [60, 85]
  }
}
```

**Validation:**
- KPI code must start with `CUSTOM-`
- KPI code must be uppercase alphanumeric with hyphens
- Target must be within range
- Range min must be < range max

**Response:**
```json
{
  "success": true,
  "message": "Custom KPI added"
}
```

---

### PUT /api/dc2s/config/custom-kpi/:kpi_code

Update a custom KPI.

**Request Body:**
```json
{
  "kpi_definition": {
    "target": 80.0,
    "range": [65, 90]
  }
}
```

---

### DELETE /api/dc2s/config/custom-kpi/:kpi_code

Delete a custom KPI.

**Response:**
```json
{
  "success": true,
  "message": "Custom KPI deleted"
}
```

---

## Scores API

### POST /api/dc2s/scores/calculate

Calculate scores for accounts.

**Request Body:**
```json
{
  "account_id": 1001,  // Optional - if omitted, calculates all accounts
  "measurement_month": "2024-12-01"  // Optional - defaults to current month
}
```

**Response:**
```json
{
  "success": true,
  "measurement_month": "2024-12-01",
  "total_accounts": 19,
  "successful": 9,
  "failed": 10,
  "results": {
    "1001": {
      "kpi_scores": [...],
      "pillar_scores": [...],
      "health_score": {...}
    }
  }
}
```

---

### GET /api/dc2s/scores/account/:account_id/latest

Get latest scores for an account.

**Response:**
```json
{
  "account_id": 1001,
  "measurement_month": "2024-12-01",
  "health_score": {
    "health_score": 75.5,
    "health_status": "good",
    "trend": "stable",
    "contributing_pillars": {
      "AI": 78.5,
      "CH": 84.1,
      "DV": 35.5,
      "EX": 75.0,
      "OS": 45.6
    }
  },
  "pillar_scores": [...],
  "kpi_scores": [...]
}
```

---

### GET /api/dc2s/scores/customer/summary

Get score summary for all customer accounts.

**Response:**
```json
{
  "customer_id": 9,
  "total_accounts": 19,
  "accounts_with_scores": 9,
  "average_health_score": 68.89,
  "status_distribution": {
    "good": 3,
    "warning": 6
  },
  "accounts": [
    {
      "account_id": 1001,
      "account_name": "Account 1",
      "health_score": 75.0,
      "health_status": "good",
      "trend": "stable",
      "measurement_month": "2024-12-01"
    }
  ]
}
```

---

### GET /api/dc2s/scores/account/:account_id/history

Get historical scores for an account.

**Query Parameters:**
- `months` (optional): Number of months to retrieve (default: 12)

**Response:**
```json
{
  "account_id": 1001,
  "months": 12,
  "history": [
    {
      "health_score": 75.0,
      "health_status": "good",
      "measurement_month": "2024-12-01"
    }
  ]
}
```

---

### GET /api/dc2s/scores/account/:account_id/pillars/:pillar_code

Get detailed breakdown for a specific pillar.

**Response:**
```json
{
  "account_id": 1001,
  "pillar_code": "AI",
  "measurement_month": "2024-12-01",
  "pillar_score": 78.53,
  "pillar_status": "good",
  "kpi_weights": {
    "AI-KPI1": 0.4,
    "AI-KPI2": 0.3
  },
  "kpi_details": [...]
}
```

---

## Error Responses

All endpoints return standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid input)
- `401`: Unauthorized (not authenticated)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error

**Error Response Format:**
```json
{
  "error": "Error message describing what went wrong"
}
```

---

## Rate Limiting

Currently no rate limiting is implemented. For production, consider:
- Rate limiting per customer
- Request throttling for score calculation
- Caching for frequently accessed data

---

## Versioning

Current API version: `v1`

No versioning scheme implemented yet. For production, consider:
- URL versioning: `/api/v1/dc2s/config/`
- Header versioning: `X-API-Version: 1`

---

## Examples

### Complete Configuration Workflow

```bash
# 1. Login
curl -X POST http://localhost:5059/api/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}' \
  -c cookies.txt

# 2. Get current config
curl -X GET http://localhost:5059/api/dc2s/config/ \
  -b cookies.txt

# 3. Update pillar weights
curl -X PUT http://localhost:5059/api/dc2s/config/pillar-weights \
  -b cookies.txt \
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

# 4. Add custom KPI
curl -X POST http://localhost:5059/api/dc2s/config/custom-kpi \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "kpi_code": "CUSTOM-GPU-TEMP",
    "kpi_definition": {
      "pillar": "AI",
      "name": "GPU Temperature",
      "unit": "°C",
      "target": 75.0,
      "operator": "<",
      "range": [60, 85]
    }
  }'

# 5. Calculate scores
curl -X POST http://localhost:5059/api/dc2s/scores/calculate \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "measurement_month": "2024-12-01"
  }'

# 6. Get latest scores
curl -X GET http://localhost:5059/api/dc2s/scores/account/1001/latest \
  -b cookies.txt
```

---

## Support

For API issues:
- Check error messages in response
- Verify authentication (session cookie)
- Review request format matches documentation
- Contact system administrator
