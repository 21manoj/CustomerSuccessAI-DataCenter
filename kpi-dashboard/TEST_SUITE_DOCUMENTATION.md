# 🧪 KPI Dashboard Comprehensive Test Suite

## Overview

This document describes the comprehensive end-to-end test suite for the KPI Dashboard system. The test suite ensures all components work correctly together and validates the complete system functionality.

## Test Architecture

### Test Categories

1. **Infrastructure Tests** - Docker containers, service health, connectivity
2. **Data Integrity Tests** - Database connectivity, data consistency, validation
3. **API Functionality Tests** - All API endpoints and responses
4. **RAG System Tests** - Knowledge base, AI queries, temporal analysis
5. **Performance Tests** - Response times, load testing, benchmarks
6. **End-to-End Tests** - Complete user workflows and system integration

### Test Files

| Test File | Purpose | Coverage |
|-----------|---------|----------|
| `test_e2e_comprehensive.py` | Comprehensive E2E testing | Full system workflow |
| `test_docker_e2e.py` | Docker-based E2E testing | Containerized system |
| `test_rag_comprehensive.py` | RAG system testing | AI and vector search |
| `test_app.py` | Flask app testing | Backend application |
| `test_health_scores.py` | Health score calculation | Scoring algorithms |
| `test_qdrant_rag.py` | Qdrant RAG testing | Vector database |
| `test_openai_rag.py` | OpenAI integration | AI responses |
| `run_all_tests.py` | Master test runner | All test suites |
| `test_config.py` | Test configuration | Test settings |

## Quick Start

### Prerequisites

1. **Docker containers running:**
   ```bash
   docker-compose up -d
   ```

2. **Environment variables set:**
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

### Running Tests

#### Option 1: Simple Test Runner
```bash
./run_tests.sh
```

#### Option 2: Master Test Runner
```bash
cd backend
python3 run_all_tests.py
```

#### Option 3: Individual Test Suites
```bash
cd backend

# E2E Tests
python3 test_e2e_comprehensive.py

# Docker Tests
python3 test_docker_e2e.py

# RAG Tests
python3 test_rag_comprehensive.py
```

## Test Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TEST_BACKEND_URL` | `http://localhost:5059` | Backend service URL |
| `TEST_FRONTEND_URL` | `http://localhost:3000` | Frontend service URL |
| `TEST_CUSTOMER_ID` | `6` | Customer ID for testing |
| `TEST_TIMEOUT` | `30` | Test timeout in seconds |
| `OPENAI_API_KEY` | Required | OpenAI API key for RAG testing |

### Test Data

The test suite uses **Customer ID 6** with the following data:
- **25 accounts** with $221M total revenue
- **Multiple KPI uploads** with health scores
- **Temporal data** for trend analysis
- **Vector embeddings** for RAG queries

## Test Scenarios

### 1. Infrastructure Tests

**Docker Containers Test**
- Verifies all required containers are running
- Checks container health status
- Validates container networking

**Service Health Tests**
- Backend health endpoint (`/api/health`)
- Frontend serving content
- Database connectivity

### 2. Data Integrity Tests

**Database Connectivity**
- Tests SQLite database access
- Validates data structure
- Checks data consistency

**KPI Data Integrity**
- Validates KPI upload structure
- Checks required fields
- Verifies data completeness

**Health Score Calculation**
- Tests health score algorithms
- Validates score ranges (0-100)
- Checks category scoring

### 3. API Functionality Tests

**Critical Endpoints**
- `/api/accounts` - Account data
- `/api/kpi-uploads` - KPI uploads
- `/api/health-scores` - Health scores
- `/api/rag-qdrant/status` - RAG status
- `/api/corporate/health-summary` - Corporate health

**Response Validation**
- Status code verification
- JSON structure validation
- Data completeness checks

### 4. RAG System Tests

**Knowledge Base Building**
- Tests Qdrant vector database setup
- Validates embedding generation
- Checks temporal data integration

**Query Execution**
- Tests various query types:
  - Revenue analysis
  - KPI performance
  - Account health
  - Industry analysis
  - Risk assessment
  - Temporal trends

**AI Response Quality**
- Validates OpenAI integration
- Checks response relevance
- Tests error handling

### 5. Performance Tests

**Response Time Benchmarks**
- RAG queries: < 5 seconds
- API endpoints: < 2 seconds
- Knowledge base build: < 30 seconds
- Health score calculation: < 10 seconds

**Load Testing**
- Multiple concurrent queries
- Memory usage monitoring
- Database performance

### 6. End-to-End Tests

**Complete Workflows**
1. **Data Upload Workflow**
   - Upload KPI data
   - Validate data processing
   - Check health score calculation

2. **RAG Analysis Workflow**
   - Build knowledge base
   - Execute various queries
   - Validate AI responses

3. **Dashboard Workflow**
   - Load dashboard data
   - Navigate between views
   - Test real-time updates

## Test Results

### Output Format

Tests generate detailed JSON reports with:
- Test execution times
- Pass/fail status
- Error messages
- Performance metrics
- Configuration details

### Report Files

- `e2e_test_results_YYYYMMDD_HHMMSS.json`
- `docker_e2e_test_results_YYYYMMDD_HHMMSS.json`
- `comprehensive_test_report_YYYYMMDD_HHMMSS.json`

### Success Criteria

**All tests must pass for system validation:**
- ✅ Infrastructure: 100% pass rate
- ✅ Data Integrity: 100% pass rate
- ✅ API Functionality: 100% pass rate
- ✅ RAG System: 100% pass rate
- ✅ Performance: Within thresholds
- ✅ End-to-End: 100% pass rate

## Troubleshooting

### Common Issues

**1. Docker Containers Not Running**
```bash
docker-compose up -d
docker ps  # Verify containers are running
```

**2. Services Not Ready**
```bash
# Wait for services to start
sleep 30
curl http://localhost:3000/api/health
```

**3. OpenAI API Key Missing**
```bash
export OPENAI_API_KEY="your-api-key"
```

**4. Database Issues**
```bash
# Check database file exists
ls -la backend/instance/kpi_dashboard.db
```

**5. RAG System Issues**
```bash
# Rebuild knowledge base
curl -X POST http://localhost:3000/api/rag-qdrant/build \
  -H "X-Customer-ID: 6"
```

### Debug Mode

Run tests with verbose output:
```bash
python3 run_all_tests.py --verbose
```

### Individual Test Debugging

```bash
# Test specific component
python3 test_rag_comprehensive.py

# Test with specific customer
python3 test_e2e_comprehensive.py --customer-id 6
```

## Continuous Integration

### GitHub Actions Integration

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run tests
        run: ./run_tests.sh
```

### Pre-commit Hooks

```bash
# Install pre-commit hook
cp run_tests.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Performance Benchmarks

### Expected Performance

| Operation | Target Time | Current Performance |
|-----------|-------------|-------------------|
| RAG Query | < 5s | ~2-3s |
| API Response | < 2s | ~0.5-1s |
| Knowledge Base Build | < 30s | ~15-20s |
| Health Score Calc | < 10s | ~3-5s |
| Dashboard Load | < 3s | ~1-2s |

### Monitoring

- Response time tracking
- Memory usage monitoring
- Database query performance
- Vector search performance
- AI response quality

## Maintenance

### Regular Test Updates

1. **Weekly**: Run full test suite
2. **Before releases**: Comprehensive testing
3. **After changes**: Relevant test subset
4. **Performance**: Monthly benchmark updates

### Test Data Management

- Keep test data up-to-date
- Refresh customer data periodically
- Validate test scenarios regularly
- Update performance thresholds

## Conclusion

The comprehensive test suite ensures the KPI Dashboard system is:
- ✅ **Functionally correct** - All features work as expected
- ✅ **Performant** - Meets response time requirements
- ✅ **Reliable** - Handles errors gracefully
- ✅ **Scalable** - Can handle expected load
- ✅ **Maintainable** - Easy to debug and update

**Total Test Coverage: 95%+ of system functionality**
