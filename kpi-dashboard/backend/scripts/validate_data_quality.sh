#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     COMPLETE DATA QUALITY VALIDATION - CUSTOMER 122        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

CUSTOMER_ID=122
ACCOUNTS="10021,10022,10023"
DATABASE_URL=postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter
echo "1️⃣  Checking configuration..."
psql $DATABASE_URL -tAc "
SELECT COUNT(*) FROM customer_configs WHERE customer_id = $CUSTOMER_ID
" | grep -q "1" && echo "   ✅ Config exists" || echo "   ❌ Config missing"

echo ""
echo $DATABASE_URL
echo "2️⃣  Checking data completeness..."
TOTAL=$(psql $DATABASE_URL -tAc "
SELECT COUNT(*) FROM dc2s_kpis 
WHERE account_id IN ($ACCOUNTS)
")
echo "   Total KPI records: $TOTAL"
[ "$TOTAL" -gt 400 ] && echo " l $DATABASE_URL -tAc "
SELECT COUNT(DISTINCT kpi_code) FROM dc2s_kpis 
WHERE account_id IN ($ACCOUNTS)
")
echo "   Enabled in config: $ENABLED"
echo "   Generated in data: $GENERATED"
[ "$ENABLED" = "$GENERATED" ] && echo "   ✅ Match" || echo "   ⚠️  Mismatch"

echo ""
echo "4️⃣  Checking scores calculated..."
SCORES=$(psql $DATABASE_URL -tAc "
SELECT COUNT(*) FROM health_scores 
WHERE account_id IN ($ACCOUNTS)
")
echo "   Health scores: $SCORES"
[ "$SCORES" -eq 3 ] && echo "   ✅ All accounts scored" || echo "   ⚠️  Missing scores"

echo ""
echo "5️⃣  Checking CSV files..."
if [ -f "dc2_s/journey/wizard_a/config/kpi_foundation.csv" ]; then
    LINES=$(wc -l < verticals/customer9-dc2_s/journey/wizard_a/config/kpi_foundation.csv)
    echo "   ✅ kpi_foundation.csv exists ($LINES lines)"
else
    echo "   ⚠️  kpi_foundation.csv missing"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    VALIDATION COMPLETE                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
