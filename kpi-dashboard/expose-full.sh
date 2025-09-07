#!/bin/bash
# Script to expose both frontend and backend publicly using ngrok

echo "🌐 Exposing KPI Dashboard (Frontend + Backend) to the public..."

# Check if Docker containers are running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Docker containers are not running. Starting them..."
    docker-compose up -d
    sleep 10
fi

# Check if containers are healthy
echo "📊 Checking container status..."
docker-compose ps

echo ""
echo "🚀 Starting ngrok tunnels..."
echo "📱 Public URLs will be displayed below:"
echo ""

# Function to start ngrok tunnel
start_tunnel() {
    local port=$1
    local service=$2
    
    echo "🔗 Starting tunnel for $service (port $port)..."
    ngrok http $port --log=stdout | while read line; do
        if echo "$line" | grep -q "started tunnel"; then
            echo "✅ $service tunnel started successfully!"
        elif echo "$line" | grep -q "url=https://"; then
            url=$(echo "$line" | grep -o 'https://[^[:space:]]*')
            echo ""
            echo "🎉 $service PUBLIC URL:"
            echo "🔗 $url"
            echo ""
        fi
    done &
}

# Start tunnels for both services
start_tunnel 3000 "Frontend"
start_tunnel 5059 "Backend"

echo "⏳ Waiting for tunnels to establish..."
sleep 5

echo ""
echo "📋 SHARE THESE URLs WITH YOUR COLLEAGUES:"
echo ""
echo "🖥️  Frontend (Main Application):"
echo "   https://[ngrok-url-1]"
echo ""
echo "🔧 Backend API (For API testing):"
echo "   https://[ngrok-url-2]"
echo ""
echo "🔐 Login credentials:"
echo "   Email: test@test.com"
echo "   Password: test123"
echo ""
echo "📊 Available data:"
echo "   - 25 accounts with revenue data"
echo "   - 1,475 KPIs across all accounts"
echo "   - RAG analysis capabilities"
echo "   - Health scores and analytics"
echo ""
echo "⏹️  Press Ctrl+C to stop all tunnels"

# Keep script running
wait
