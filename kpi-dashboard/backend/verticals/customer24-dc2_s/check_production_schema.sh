#!/bin/bash
# ============================================================================
# CHECK PRODUCTION SCHEMA INTEGRITY
# Verifies that production schema hasn't been modified
# ============================================================================

echo "=========================================="
echo "PRODUCTION SCHEMA INTEGRITY CHECK"
echo "=========================================="
echo ""

echo "Checking critical columns..."
echo ""

# Check kpi_measurements.measurement_id type
echo "1. Checking kpi_measurements.measurement_id..."
MEAS_TYPE=$(psql $DATABASE_URL -t -c "SELECT data_type FROM information_schema.columns WHERE table_name = 'kpi_measurements' AND column_name = 'measurement_id';")
if [[ "$MEAS_TYPE" == *"integer"* ]]; then
    echo "   ✅ measurement_id is INTEGER (correct)"
elif [[ "$MEAS_TYPE" == *"text"* ]] || [[ "$MEAS_TYPE" == *"character"* ]]; then
    echo "   ❌ measurement_id is TEXT (WRONG - production is broken!)"
    echo "      You need to revert this change immediately!"
    NEEDS_FIX=true
else
    echo "   ⚠️  measurement_id type: $MEAS_TYPE"
fi

# Check playbook_executions.execution_id type
echo "2. Checking playbook_executions.execution_id..."
EXEC_TYPE=$(psql $DATABASE_URL -t -c "SELECT data_type FROM information_schema.columns WHERE table_name = 'playbook_executions' AND column_name = 'execution_id';")
if [[ "$EXEC_TYPE" == *"integer"* ]]; then
    echo "   ✅ execution_id is INTEGER (correct)"
elif [[ "$EXEC_TYPE" == *"text"* ]] || [[ "$EXEC_TYPE" == *"character"* ]]; then
    echo "   ❌ execution_id is TEXT (WRONG - production is broken!)"
    echo "      You need to revert this change immediately!"
    NEEDS_FIX=true
else
    echo "   ⚠️  execution_id type: $EXEC_TYPE"
fi

# Check kpi_definitions column names
echo "3. Checking kpi_definitions columns..."
HAS_STATE=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'kpi_definitions' AND column_name LIKE 'state_%';")
HAS_RANGE=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'kpi_definitions' AND column_name LIKE 'range_%';")

if [ "$HAS_STATE" -gt "0" ]; then
    echo "   ✅ Has state_* columns ($HAS_STATE found) - correct"
    if [ "$HAS_RANGE" -gt "0" ]; then
        echo "   ⚠️  ALSO has range_* columns ($HAS_RANGE found) - duplicate?"
    fi
elif [ "$HAS_RANGE" -gt "0" ]; then
    echo "   ❌ Has range_* columns but NO state_* columns (WRONG)"
    echo "      Production schema has been modified!"
    NEEDS_FIX=true
else
    echo "   ⚠️  No state_* or range_* columns found"
fi

echo ""
echo "=========================================="
if [ -n "$NEEDS_FIX" ]; then
    echo "❌ PRODUCTION SCHEMA IS BROKEN"
    echo "=========================================="
    echo ""
    echo "Your production schema has been modified!"
    echo "You need to revert these changes immediately."
    echo ""
    echo "Contact me for rollback scripts."
else
    echo "✅ PRODUCTION SCHEMA IS INTACT"
    echo "=========================================="
    echo ""
    echo "Your production schema is safe."
    echo "You can proceed with fixing the CSV files."
fi
echo ""
