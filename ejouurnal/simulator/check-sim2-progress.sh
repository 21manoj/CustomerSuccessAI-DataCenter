#!/bin/bash
# Check Sim2 progress

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           SIM2 - CURRENT PROGRESS                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running
if ps aux | grep "node sim2-advanced.js" | grep -v grep > /dev/null; then
    PID=$(ps aux | grep "node sim2-advanced.js" | grep -v grep | awk '{print $2}')
    
    echo "✅ Sim2 IS RUNNING (PID: $PID)"
    echo ""
    
    # Calculate progress
    START_TIME=$(ps -p $PID -o lstart= 2>/dev/null)
    if [ -n "$START_TIME" ]; then
        CURRENT=$(date +%s)
        START_EPOCH=$(date -j -f "%a %b %d %H:%M:%S %Y" "$START_TIME" +%s 2>/dev/null || echo "0")
        
        if [ "$START_EPOCH" != "0" ]; then
            ELAPSED=$(( (CURRENT - START_EPOCH) / 60 ))
            CURRENT_DAY=$(( ELAPSED / 10 + 1 ))
            REMAINING=$(( 240 - ELAPSED ))
            
            echo "⏰ TIMELINE:"
            echo "   Started: $START_TIME"
            echo "   Elapsed: $ELAPSED minutes"
            echo "   Current Day: ~$CURRENT_DAY of 24"
            echo "   Remaining: ~$REMAINING minutes (~$(( REMAINING / 60 ))h $(( REMAINING % 60 ))m)"
            echo "   Progress: $(( ELAPSED * 100 / 240 ))%"
            echo ""
        fi
    fi
    
    echo "📊 Check terminal for live output or wait for completion."
    echo "   Will complete at: ~12:54 AM"
else
    echo "❌ Sim2 NOT running"
    echo ""
    echo "Check for results:"
    ls -lht output/sim2-* 2>/dev/null | head -5
fi

echo ""

