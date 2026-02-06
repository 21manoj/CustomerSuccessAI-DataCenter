#!/bin/bash
# Start Backend Server
# NOTE: This script no longer starts local Qdrant server
# We are using Qdrant Cloud now. Please set QDRANT_URL and QDRANT_API_KEY in your .env file

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "🚀 Starting KPI Dashboard Backend Server..."
echo ""

# Check for Qdrant Cloud configuration
if [ -z "$QDRANT_URL" ] && [ -f .env ]; then
    # Try to get from .env file
    if grep -q "QDRANT_URL" .env 2>/dev/null; then
        export $(grep -v '^#' .env | grep QDRANT_URL | xargs)
    fi
fi

if [ -z "$QDRANT_URL" ]; then
    echo "⚠️  WARNING: QDRANT_URL not set"
    echo "   Please configure QDRANT_URL and QDRANT_API_KEY in your .env file"
    echo "   Qdrant features will be disabled until configured"
    echo ""
fi

echo "Step 1/1: Starting Backend Server..."

# Step 2: Check if backend is already running
if lsof -ti:5059 > /dev/null 2>&1; then
    echo "⚠️  Backend is already running on port 5059"
    echo "   To restart, stop it first: kill \$(lsof -ti:5059)"
    exit 0
fi

# Step 3: Run startup checks (optional)
if [ -f "${SCRIPT_DIR}/startup_checks.sh" ]; then
    echo "📋 Running startup checks..."
    bash "${SCRIPT_DIR}/startup_checks.sh"
    echo ""
fi

# Step 4: Start backend server
echo "🔄 Starting backend server..."
nohup python3 app_v3_minimal.py > backend.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for server to start
sleep 3

# Check if backend started successfully
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "✅ Backend server started (PID: $BACKEND_PID)"
    echo "   Logs: ${SCRIPT_DIR}/backend.log"
    echo "   Health: http://localhost:5059/api/health"
    echo ""
    echo "To stop backend:"
    echo "  kill $BACKEND_PID"
else
    echo "❌ Backend server failed to start"
    echo "   Check logs: tail -50 ${SCRIPT_DIR}/backend.log"
    exit 1
fi

echo ""
echo "🎉 All services started successfully!"
