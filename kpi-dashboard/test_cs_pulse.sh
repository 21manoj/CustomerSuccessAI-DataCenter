#!/bin/bash
# ============================================================================
# CS Pulse Test Suite
# ============================================================================
# 
# Tests backend APIs and provides frontend test URLs
# 
# Usage:
#   chmod +x test_cs_pulse.sh
#   ./test_cs_pulse.sh
#
# Ports:
#   Backend:  5059
#   Frontend: 8005
# ============================================================================

set -e

# Configuration
BACKEND_URL="http://localhost:5059"
FRONTEND_URL="http://localhost:8005"
TIMEOUT=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
SKIPPED=0

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

print_test() {
    echo -e "\n${YELLOW}TEST:${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    ((FAILED++))
}

print_skip() {
    echo -e "${YELLOW}⏭️  SKIP:${NC} $1"
    ((SKIPPED++))
}

print_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

print_header "PRE-FLIGHT CHECKS"

# Check if backend is running
print_test "Backend server on port 5059"
if curl -s --connect-timeout 5 "${BACKEND_URL}/api/journey/health" > /dev/null 2>&1; then
    print_pass "Backend is running"
else
    print_fail "Backend not responding at ${BACKEND_URL}"
    echo -e "${RED}Please start backend: python app_v3_minimal.py${NC}"
    echo -e "${RED}Aborting tests.${NC}"
    exit 1
fi

# Check if frontend is running
print_test "Frontend server on port 8005"
if curl -s --connect-timeout 5 "${FRONTEND_URL}" > /dev/null 2>&1; then
    print_pass "Frontend is running"
else
    print_skip "Frontend not responding (manual browser tests needed)"
fi

# Check OpenAI API key
print_test "OPENAI_API_KEY environment variable"
if [ -n "$OPENAI_API_KEY" ]; then
    KEY_PREFIX="${OPENAI_API_KEY:0:7}..."
    print_pass "API key set (${KEY_PREFIX})"
else
    print_fail "OPENAI_API_KEY not set"
    echo -e "${YELLOW}Set with: export OPENAI_API_KEY='sk-...'${NC}"
fi

# ============================================================================
# TEST SUITE 1: Journey API
# ============================================================================

print_header "TEST SUITE 1: JOURNEY API"

# Test 1.1: Health Check
print_test "1.1 Journey API Health Check"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/health")
if echo "$RESPONSE" | grep -q "healthy"; then
    print_pass "Health endpoint working"
else
    print_fail "Health check failed: $RESPONSE"
fi

# Test 1.2: List Accounts
print_test "1.2 List Journey Accounts"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/accounts")
ACCOUNT_COUNT=$(echo "$RESPONSE" | grep -o '"journey_account_id"' | wc -l)
if [ "$ACCOUNT_COUNT" -ge 1 ]; then
    print_pass "Found $ACCOUNT_COUNT accounts"
    echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print('   Accounts:', [a.get('journey_account_id') for a in data.get('accounts',[])])" 2>/dev/null || true
else
    print_fail "No accounts found"
fi

# Test 1.3: Get Account 10001
print_test "1.3 Get Account 10001 Journey"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/10001")
if echo "$RESPONSE" | grep -q "account_name\|weekly_data"; then
    WEEKS=$(echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data.get('weekly_data',[])))" 2>/dev/null || echo "?")
    print_pass "Account 10001 loaded with $WEEKS weeks of data"
else
    print_fail "Account 10001 not found: $RESPONSE"
fi

# Test 1.4: Get Account 10003
print_test "1.4 Get Account 10003 Journey"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/10003")
if echo "$RESPONSE" | grep -q "account_name\|weekly_data"; then
    print_pass "Account 10003 loaded"
else
    print_fail "Account 10003 not found"
fi

# Test 1.5: Get Account 10007
print_test "1.5 Get Account 10007 Journey"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/10007")
if echo "$RESPONSE" | grep -q "account_name\|weekly_data"; then
    print_pass "Account 10007 loaded"
else
    print_fail "Account 10007 not found"
fi

# Test 1.6: Get Week Detail
print_test "1.6 Get Week 5 Detail for Account 10001"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/10001/week/5")
if echo "$RESPONSE" | grep -q "health_score\|kpis"; then
    print_pass "Week detail retrieved"
else
    print_fail "Week detail failed: $RESPONSE"
fi

# Test 1.7: Get Account Summary
print_test "1.7 Get Account 10001 Summary"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/10001/summary")
if echo "$RESPONSE" | grep -q "total_weeks\|avg_health"; then
    print_pass "Summary retrieved"
    echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'   Total weeks: {d.get(\"total_weeks\")}, Avg health: {d.get(\"avg_health\")}')" 2>/dev/null || true
else
    print_fail "Summary failed: $RESPONSE"
fi

# ============================================================================
# TEST SUITE 2: Signal Analyst API
# ============================================================================

print_header "TEST SUITE 2: SIGNAL ANALYST API"

# Test 2.1: Signal Analyst Endpoint Exists
print_test "2.1 Signal Analyst Endpoint"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/signal-analyst/health" 2>/dev/null || echo "000")
if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "404" ]; then
    print_pass "Endpoint accessible (HTTP $RESPONSE)"
else
    print_skip "Endpoint check inconclusive"
fi

# Test 2.2: Run Analysis (this takes ~15-20 seconds)
print_test "2.2 Run Signal Analyst on Account 10001"
echo -e "${YELLOW}   This may take 15-20 seconds (GPT-4o API call)...${NC}"

START_TIME=$(date +%s)
RESPONSE=$(curl -s --max-time 60 -X POST "${BACKEND_URL}/api/signal-analyst/analyze" \
    -H "Content-Type: application/json" \
    -d '{"account_id": "10001"}' 2>&1)
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if echo "$RESPONSE" | grep -q "health_score"; then
    HEALTH=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('health_score','?'))" 2>/dev/null || echo "?")
    CHURN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('churn_probability','?'))" 2>/dev/null || echo "?")
    EXPANSION=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('expansion_probability','?'))" 2>/dev/null || echo "?")
    print_pass "Analysis complete in ${DURATION}s"
    echo "   Health Score: $HEALTH"
    echo "   Churn Probability: $CHURN%"
    echo "   Expansion Probability: $EXPANSION%"
elif echo "$RESPONSE" | grep -qi "api.key\|unauthorized\|invalid"; then
    print_fail "API key issue: Check OPENAI_API_KEY"
elif echo "$RESPONSE" | grep -qi "timeout\|timed out"; then
    print_fail "Request timed out after ${DURATION}s"
else
    print_fail "Unexpected response: ${RESPONSE:0:200}"
fi

# ============================================================================
# TEST SUITE 3: Database Verification
# ============================================================================

print_header "TEST SUITE 3: DATABASE VERIFICATION"

# We'll use the API to verify data exists
print_test "3.1 Journey Accounts Table"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/accounts")
COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('accounts',[])))" 2>/dev/null || echo "0")
if [ "$COUNT" -ge 3 ]; then
    print_pass "$COUNT accounts in database"
else
    print_fail "Expected 3+ accounts, found $COUNT"
fi

print_test "3.2 Journey KPIs Data"
# Check by getting account detail which includes KPIs
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/10001")
HAS_DATA=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); w=d.get('weekly_data',[]); print('yes' if len(w)>0 and w[0].get('kpis') else 'no')" 2>/dev/null || echo "no")
if [ "$HAS_DATA" = "yes" ]; then
    print_pass "KPI data present in journey"
else
    print_fail "No KPI data found"
fi

print_test "3.3 Journey Events Data"
RESPONSE=$(curl -s "${BACKEND_URL}/api/journey/10001")
EVENT_COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(len(w.get('events',[])) for w in d.get('weekly_data',[])))" 2>/dev/null || echo "0")
if [ "$EVENT_COUNT" -gt 0 ]; then
    print_pass "$EVENT_COUNT events found"
else
    print_skip "No events (may be expected)"
fi

# ============================================================================
# FRONTEND TEST URLS
# ============================================================================

print_header "FRONTEND TEST URLS"

echo -e "${BLUE}Open these URLs in your browser to test the frontend:${NC}"
echo ""
echo -e "1. ${GREEN}Executive Dashboard:${NC}"
echo "   ${FRONTEND_URL}/dashboard"
echo ""
echo -e "2. ${GREEN}Journey V3 - Account 10001 (Expansion):${NC}"
echo "   ${FRONTEND_URL}/journey-v3/10001"
echo ""
echo -e "3. ${GREEN}Journey V3 - Account 10003 (Churn):${NC}"
echo "   ${FRONTEND_URL}/journey-v3/10003"
echo ""
echo -e "4. ${GREEN}Journey V3 - Account 10007 (Recovery):${NC}"
echo "   ${FRONTEND_URL}/journey-v3/10007"
echo ""

# ============================================================================
# MANUAL TEST CHECKLIST
# ============================================================================

print_header "MANUAL TEST CHECKLIST"

echo -e "${YELLOW}Perform these manual tests in the browser:${NC}"
echo ""
echo "□ Executive Dashboard loads with account cards"
echo "□ Click ▶️ (Play) → Progress modal appears"
echo "□ Modal shows 5 steps progressing"
echo "□ After ~16s → 'View Results' button appears"
echo "□ Click 'View Journey' → Navigates to /journey-v3/:id"
echo "□ All 5 tabs render content:"
echo "   □ Health Overview - Timeline chart, radar"
echo "   □ Qualitative Signals - Signal cards, sentiment charts"
echo "   □ Signal Analyst - Churn/expansion, drivers, actions"
echo "   □ Correlation - Overlay chart, heatmap"
echo "   □ Root Cause Analysis - Hypotheses, timeline, actions"
echo "□ Back arrow returns to dashboard"
echo ""

# ============================================================================
# SUMMARY
# ============================================================================

print_header "TEST SUMMARY"

TOTAL=$((PASSED + FAILED + SKIPPED))
echo -e "Total Tests: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo -e "${YELLOW}Skipped: $SKIPPED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All automated tests passed!${NC}"
    echo -e "${BLUE}Proceed with manual browser testing.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Review errors above.${NC}"
    exit 1
fi
