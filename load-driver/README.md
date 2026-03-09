# CS Pulse External Load Driver

Non-intrusive E2E testing suite for CS Pulse platform. Runs completely decoupled from the main application, simulating real-world customer journeys and system behavior.

## Quick Start

### Option 1: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
export CS_PULSE_BASE_URL=http://localhost:5059
export OPENAI_API_KEY=sk-...
export QDRANT_URL=http://localhost:6333

# Run all scenarios for 3 customers
python driver.py --scenarios 1,2a,2b,2c,2d,2e,3,4,5,6 --customers 1,2,3

# View results
cat results/LOAD_TEST_RESULTS.md
```

### Option 2: Docker (Recommended)

```bash
# Prerequisites: docker, docker-compose, running CS Pulse instance

# Create network (if not using external)
docker network create cspulse

# Start CS Pulse first
cd ..
docker-compose up -d

# Start load drivers (3 parallel customers)
docker-compose -f docker-compose.loaddriver.yml up -d

# Monitor progress
docker logs -f cspulse-load-driver-cust-1
docker logs -f cspulse-load-driver-cust-2
docker logs -f cspulse-load-driver-cust-3

# Check results
ls results/customer-{1,2,3}/LOAD_TEST_RESULTS.md
```

## Scenarios

| # | Name | Description | Duration |
|---|------|-------------|----------|
| **1** | Onboarding | Register customer, create 50 accounts, process data, calculate scores | ~5-10m |
| **2a** | KPI Simulation | Mutate KPIs over 12 months, trigger recalculation | ~5m |
| **2b** | RAG Queries | 50 accounts × 3-5 natural language queries each | ~10-15m |
| **2c** | Signal Detection | Detect churn/expansion signals, trigger playbooks | ~5m |
| **2d** | RACI Reports | Fetch execution reports, validate markdown export | ~2m |
| **2e** | Churn Lifecycle | Archive + delete churned accounts, verify cascade | ~3m |
| **3** | Tenant Isolation | 12 cross-tenant security tests | ~5m |
| **4** | Post-Test Cleanup | Delete all test data (24 tables, FK-safe order) | ~2m |
| **5** | ROI Power-of-1 | Historical + forward ROI at 1%/4%/6% improvements | ~3m |
| **6** | N8N Workflow | Trigger playbooks, verify Google Sheets mock output | ~10m |

**Total per customer:** ~50-60 minutes

## Command-Line Options

```bash
python driver.py \
  --scenarios 1,2a,2b,2c,2d,2e,3,4,5,6  \
  --customers 1,2,3                      \
  --base-url http://localhost:5059       \
  --results-dir results                  \
  --dry-run                              \
  --verbose
```

### Arguments

| Argument | Default | Example | Notes |
|----------|---------|---------|-------|
| `--scenarios` | All | `1,2a,2b` | Comma-separated scenario IDs |
| `--customers` | 1,2,3 | `1` | Comma-separated customer IDs |
| `--base-url` | `http://localhost:5059` | — | CS Pulse backend URL |
| `--results-dir` | `results` | `/tmp/test-results` | Output directory |
| `--dry-run` | False | (flag) | Preview without changes |
| `--verbose` | False | (flag) | Enable DEBUG logging |

## Configuration

### Environment Variables

```bash
# Required
CS_PULSE_BASE_URL=http://localhost:5059

# Optional (defaults: admin@sacme.com / test123, customer 291)
CS_PULSE_ADMIN_EMAIL=admin@sacme.com
CS_PULSE_ADMIN_PASSWORD=test123
OPENAI_API_KEY=sk-...
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=...
LOG_LEVEL=INFO
```

### .env File

```bash
# Create .env from template
cp .env.example .env

# Edit with your configuration
nano .env
```

## Output

Results are saved to `results/` directory:

```
results/
├── LOAD_TEST_RESULTS.md          # Human-readable report
├── LOAD_TEST_RESULTS.json        # Raw results (machine-readable)
└── load_driver.log               # Detailed execution log
```

### Report Contents

- Executive summary (success rate, scenario breakdown)
- Detailed results per scenario
- API call counts and timing
- Errors and warnings
- Raw JSON for analysis

Example:
```markdown
# Load Test Results
Generated: 2026-02-24 10:30:45
Base URL: http://localhost:5059

## Executive Summary
- Total Scenarios: 10
- Completed: 9
- Failed: 1
- Success Rate: 90.0%

## Scenario Results
✅ onboarding
- Status: COMPLETED
- Customer 1: 50 accounts created, data processed
...
```

## Advanced Usage

### Run Single Scenario

```bash
# Only customer registration
python driver.py --scenarios 1 --customers 1

# Only cleanup (dry-run)
python driver.py --scenarios 4 --customers 1 --dry-run

# Only playbooks
python driver.py --scenarios 2c,2d --customers 1,2
```

### Parallel Multi-Customer Testing

```bash
# Run driver 3 times in parallel (different terminals)
python driver.py --customers 1 &
python driver.py --customers 2 &
python driver.py --customers 3 &
wait

# Or use Docker Compose
docker-compose -f docker-compose.loaddriver.yml up --scale load-driver-customer=3
```

### Debug Mode

```bash
# Verbose logging + halt on first error
python driver.py \
  --verbose \
  --dry-run \
  --scenarios 1 \
  --customers 1
```

## Architecture

### Components

1. **driver.py** — Orchestrator
   - Loads scenarios dynamically
   - Manages customer clients
   - Collects and aggregates results
   - Generates reports

2. **client.py** — HTTP Client
   - Session-based authentication
   - Automatic retry with exponential backoff
   - Health checks
   - Request/response logging

3. **scenarios/** — Test Scenarios
   - `base.py` — Abstract base class
   - `scenario_*.py` — Concrete implementations
   - Measure API calls, timing, success rates

4. **Dockerfile** — Container Image
   - Python 3.11 slim base
   - Dependencies pre-installed
   - Results volume mount

### Data Flow

```
driver.py
  ├── Load scenarios/
  ├── Create client per customer
  ├── For each scenario:
  │   ├── scenario_N.run()
  │   │   ├── client.register_customer()
  │   │   ├── client.complete_onboarding()
  │   │   ├── client.process_data()
  │   │   ├── client.calculate_scores()
  │   │   └── ...
  │   └── Collect results
  └── Generate report
```

## Troubleshooting

### Connection Refused

```
Error: Connection refused: http://localhost:5059
```

**Fix:** Start CS Pulse backend first:
```bash
cd ../kpi-dashboard/backend
python app_v3_minimal.py
```

### Authentication Failed

```
❌ Login failed: {'status': 'error', 'error': 'Invalid email or password'}
```

**Fix:** Check credentials in environment or code:
```bash
export CS_PULSE_ADMIN_EMAIL=correct@email.com
export CS_PULSE_ADMIN_PASSWORD=correctpassword
```

### Timeout on Data Processing

```
⏱️  Data processing timed out (may still be in progress)
```

**Expected behavior** for large datasets. Processing happens async. Re-run later to continue.

### Orphan Rows After Cleanup

```
⚠️  Verification: 5 orphan rows found in dc2s_kpis
```

**Known issue:** Some tables lack `customer_id` FK. See EXTERNAL_LOAD_DRIVER_GAP_ANALYSIS.md GAP-LD-27.

## Performance Baselines

On a standard laptop (MacBook Pro M1, 16GB RAM):

| Scenario | 1 Customer | 3 Customers |
|----------|-----------|-----------|
| Onboarding | 8m | 24m |
| KPI Simulation | 3m | 9m |
| RAG Queries | 12m | 36m |
| Signal Detection | 4m | 12m |
| RACI Reports | 2m | 6m |
| Churn Lifecycle | 2m | 6m |
| Tenant Isolation | 5m | 15m |
| Cleanup | 1m | 3m |
| ROI Power-of-1 | 2m | 6m |
| N8N Workflow | 8m | 24m |
| **TOTAL** | **~47m** | **~141m** |

## CI/CD Integration

### GitHub Actions

```yaml
name: Load Test
on: [push, workflow_dispatch]

jobs:
  load-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: cspulse
          POSTGRES_USER: cspulse
          POSTGRES_PASSWORD: cspulse
      qdrant:
        image: qdrant/qdrant:latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd load-driver
          pip install -r requirements.txt

      - name: Run load test
        env:
          CS_PULSE_BASE_URL: http://localhost:5059
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cd load-driver
          python driver.py \
            --scenarios 1,2a,2b,2c,2d,2e,3,4,5,6 \
            --customers 1,2,3 \
            --results-dir results

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: load-test-results
          path: load-driver/results/
```

## Contributing

Add new scenarios by:

1. Create `scenarios/scenario_YOUR_NAME.py`
2. Inherit from `BaseScenario`
3. Implement `run()` method
4. Register in `driver.py`:
   ```python
   SCENARIOS = {
       'X': 'your_name',
       ...
   }
   ```

## License

Same as parent repository (CustomerSuccessAI-DataCenter)
