#!/bin/bash
# Test Qdrant RAG API endpoints using curl

BASE_URL="http://localhost:5059"

echo "======================================================================"
echo "QDRANT RAG API TEST WITH CURL"
echo "======================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Login
echo "[1/4] Testing Login..."
LOGIN_RESPONSE=$(curl -s -c /tmp/cookies.txt -X POST "${BASE_URL}/api/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@syntara.com","password":"syntara123","remember":false}')

echo "$LOGIN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"

LOGIN_STATUS=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'unknown'))" 2>/dev/null || echo "unknown")

if [ "$LOGIN_STATUS" != "success" ]; then
    echo -e "${RED}❌ Login failed${NC}"
    echo ""
    echo "Please provide correct credentials:"
    echo "  Email: ?"
    echo "  Password: ?"
    exit 1
fi

echo -e "${GREEN}✅ Login successful${NC}"
CUSTOMER_ID=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('user', {}).get('customer_id', 'unknown'))" 2>/dev/null || echo "unknown")
echo "   Customer ID: $CUSTOMER_ID"
echo ""

# Step 2: Build Knowledge Base
echo "[2/4] Building Qdrant Knowledge Base..."
BUILD_RESPONSE=$(curl -s -b /tmp/cookies.txt -X POST "${BASE_URL}/api/rag-qdrant/build" \
  -H "Content-Type: application/json" \
  --max-time 120)

echo "$BUILD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$BUILD_RESPONSE"

BUILD_STATUS=$(echo "$BUILD_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'unknown'))" 2>/dev/null || echo "unknown")

if [ "$BUILD_STATUS" = "success" ]; then
    echo -e "${GREEN}✅ Knowledge base built successfully${NC}"
    COLLECTION_INFO=$(echo "$BUILD_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); info=data.get('collection_info', {}); print(f\"Collection: {info.get('collection_name', 'N/A')}, Points: {info.get('points_count', 0)}\")" 2>/dev/null || echo "")
    echo "   $COLLECTION_INFO"
else
    echo -e "${YELLOW}⚠️  Build returned: $BUILD_STATUS (may already exist)${NC}"
fi
echo ""

# Step 3: Test Query 1 - Revenue Analysis
echo "[3/4] Testing Query: Revenue Analysis..."
QUERY1_RESPONSE=$(curl -s -b /tmp/cookies.txt -X POST "${BASE_URL}/api/rag-qdrant/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"Which accounts have the highest revenue?","query_type":"revenue_analysis","conversation_history":[]}' \
  --max-time 60)

QUERY1_STATUS=$(echo "$QUERY1_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('error' if 'error' in data else 'success')" 2>/dev/null || echo "unknown")

if [ "$QUERY1_STATUS" = "success" ]; then
    echo -e "${GREEN}✅ Query 1 successful${NC}"
    RESULTS_COUNT=$(echo "$QUERY1_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('results_count', 0))" 2>/dev/null || echo "0")
    RESPONSE_PREVIEW=$(echo "$QUERY1_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); resp=data.get('response', ''); print(resp[:200])" 2>/dev/null || echo "")
    echo "   Results: $RESULTS_COUNT"
    echo "   Response preview: ${RESPONSE_PREVIEW}..."
else
    echo -e "${RED}❌ Query 1 failed${NC}"
    echo "$QUERY1_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$QUERY1_RESPONSE" | head -20
fi
echo ""

# Step 4: Test Query 2 - Account Health
echo "[4/4] Testing Query: Account Health..."
QUERY2_RESPONSE=$(curl -s -b /tmp/cookies.txt -X POST "${BASE_URL}/api/rag-qdrant/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"Show me account health scores and performance","query_type":"account_analysis","conversation_history":[]}' \
  --max-time 60)

QUERY2_STATUS=$(echo "$QUERY2_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print('error' if 'error' in data else 'success')" 2>/dev/null || echo "unknown")

if [ "$QUERY2_STATUS" = "success" ]; then
    echo -e "${GREEN}✅ Query 2 successful${NC}"
    RESULTS_COUNT=$(echo "$QUERY2_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('results_count', 0))" 2>/dev/null || echo "0")
    RESPONSE_PREVIEW=$(echo "$QUERY2_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); resp=data.get('response', ''); print(resp[:200])" 2>/dev/null || echo "")
    echo "   Results: $RESULTS_COUNT"
    echo "   Response preview: ${RESPONSE_PREVIEW}..."
else
    echo -e "${RED}❌ Query 2 failed${NC}"
    echo "$QUERY2_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$QUERY2_RESPONSE" | head -20
fi
echo ""

# Cleanup
rm -f /tmp/cookies.txt

echo "======================================================================"
echo "TEST COMPLETE"
echo "======================================================================"
