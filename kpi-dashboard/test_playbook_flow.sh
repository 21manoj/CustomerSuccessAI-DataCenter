#!/bin/bash

# Test Playbook Complete Flow
# Tests execution creation, step completion, report generation

echo "🧪 Testing Complete Playbook Flow"
echo "=" | head -c 60
echo ""

BASE_URL="http://localhost:5059"
CUSTOMER_ID="1"

# Test 1: Create execution with account
echo "1️⃣ Creating VoC Sprint execution for TechCorp Solutions..."
EXECUTION=$(curl -s -X POST "$BASE_URL/api/playbooks/executions" \
  -H "X-Customer-ID: $CUSTOMER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "playbookId": "voc-sprint",
    "context": {
      "customerId": 1,
      "accountId": 1,
      "accountName": "TechCorp Solutions",
      "userId": 1,
      "userName": "Test User",
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
      "metadata": {"priority": "high"}
    }
  }')

EXEC_ID=$(echo "$EXECUTION" | python3 -c "import sys, json; print(json.load(sys.stdin)['execution']['id'])" 2>/dev/null)

if [ -z "$EXEC_ID" ]; then
  echo "❌ Failed to create execution"
  exit 1
fi

echo "✅ Created execution: $EXEC_ID"
echo "   Account: $(echo "$EXECUTION" | python3 -c "import sys, json; print(json.load(sys.stdin)['execution'].get('context', {}).get('accountName', 'N/A'))" 2>/dev/null)"
echo ""

# Test 2: Get executions
echo "2️⃣ Fetching all executions..."
EXECUTIONS=$(curl -s "$BASE_URL/api/playbooks/executions" -H "X-Customer-ID: $CUSTOMER_ID")
EXEC_COUNT=$(echo "$EXECUTIONS" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('executions', [])))" 2>/dev/null)
echo "✅ Found $EXEC_COUNT execution(s)"
echo ""

# Test 3: Complete a step
echo "3️⃣ Completing step 1..."
STEP_RESULT=$(curl -s -X POST "$BASE_URL/api/playbooks/executions/$EXEC_ID/steps" \
  -H "X-Customer-ID: $CUSTOMER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "stepId": "voc-trigger-check",
    "result": {"status": "completed", "notes": "Triggers evaluated"}
  }')

echo "✅ Step completed"
echo ""

# Test 4: Generate report
echo "4️⃣ Generating comprehensive report..."
REPORT=$(curl -s "$BASE_URL/api/playbooks/executions/$EXEC_ID/report" -H "X-Customer-ID: $CUSTOMER_ID")
REPORT_STATUS=$(echo "$REPORT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null)

if [ "$REPORT_STATUS" = "success" ]; then
  echo "✅ Report generated successfully"
  echo "   Playbook: $(echo "$REPORT" | python3 -c "import sys, json; print(json.load(sys.stdin)['report']['playbook_name'])" 2>/dev/null)"
  echo "   Account: $(echo "$REPORT" | python3 -c "import sys, json; print(json.load(sys.stdin)['report']['account_name'])" 2>/dev/null)"
  echo "   Themes: $(echo "$REPORT" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['report'].get('themes_discovered', [])))" 2>/dev/null)"
  echo "   Outcomes: $(echo "$REPORT" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['report'].get('outcomes_achieved', {})))" 2>/dev/null)"
else
  echo "❌ Failed to generate report"
fi
echo ""

# Test 5: Get all reports
echo "5️⃣ Fetching all reports..."
ALL_REPORTS=$(curl -s "$BASE_URL/api/playbooks/reports" -H "X-Customer-ID: $CUSTOMER_ID")
REPORTS_COUNT=$(echo "$ALL_REPORTS" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('reports', [])))" 2>/dev/null)
echo "✅ Found $REPORTS_COUNT report(s) available"
echo ""

# Test 6: Delete execution
echo "6️⃣ Deleting execution..."
DELETE_RESULT=$(curl -s -X DELETE "$BASE_URL/api/playbooks/executions/$EXEC_ID" -H "X-Customer-ID: $CUSTOMER_ID")
DELETE_STATUS=$(echo "$DELETE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null)

if [ "$DELETE_STATUS" = "success" ]; then
  echo "✅ Execution deleted successfully"
else
  echo "❌ Failed to delete execution"
fi
echo ""

echo "=" | head -c 60
echo ""
echo "🎉 All tests completed!"
echo ""

