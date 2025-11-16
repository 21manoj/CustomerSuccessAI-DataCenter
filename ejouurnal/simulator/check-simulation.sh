#!/bin/bash
# Check 2-hour simulation progress

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     FULFILLMENT SIMULATOR - LIVE PROGRESS                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if simulation is running
if ps aux | grep "node run-simulation.js" | grep -v grep > /dev/null; then
    PID=$(ps aux | grep "node run-simulation.js" | grep -v grep | awk '{print $2}')
    START_TIME=$(ps -p $PID -o lstart= 2>/dev/null)
    
    echo "✅ Simulation IS RUNNING"
    echo "   PID: $PID"
    echo "   Started: $START_TIME"
    echo ""
    
    # Calculate how far along we are
    CURRENT_TIME=$(date +%s)
    START_EPOCH=$(date -j -f "%a %b %d %H:%M:%S %Y" "$START_TIME" +%s 2>/dev/null || echo "0")
    
    if [ "$START_EPOCH" != "0" ]; then
        ELAPSED=$(( (CURRENT_TIME - START_EPOCH) / 60 ))
        TOTAL_MINS=120
        REMAINING=$(( TOTAL_MINS - ELAPSED ))
        CURRENT_DAY=$(( ELAPSED / 10 + 1 ))
        
        echo "⏰ TIMELINE:"
        echo "   Elapsed: $ELAPSED minutes"
        echo "   Estimated Day: $CURRENT_DAY of 12"
        echo "   Remaining: $REMAINING minutes (~$(( REMAINING / 60 ))h $(( REMAINING % 60 ))m)"
        echo ""
    fi
    
    echo "📊 To see live output, check the terminal where you started it."
    echo "   Or run: tail -f <simulation-output-file>"
else
    echo "❌ Simulation NOT running"
    echo ""
    echo "   It may have:"
    echo "   1. Completed already"
    echo "   2. Been interrupted"
    echo "   3. Crashed"
    echo ""
    echo "   Check for output files:"
    ls -lht output/ 2>/dev/null | head -5
fi

echo ""
echo "📁 Latest Results:"
if [ -f "output/quick-demo-results.json" ]; then
    echo "   ✅ Quick demo: output/quick-demo-results.json"
fi

# Check for full simulation results
LATEST=$(ls -t output/simulation-*.json 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    echo "   ✅ Full simulation: $LATEST"
else
    echo "   ⏳ Full simulation: Not complete yet"
fi

echo ""

