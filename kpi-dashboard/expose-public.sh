#!/bin/bash
# Script to expose KPI Dashboard publicly using ngrok

echo "🌐 Exposing KPI Dashboard to the public..."

# Check if Docker containers are running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Docker containers are not running. Starting them..."
    docker-compose up -d
    sleep 10
fi

# Check if containers are healthy
echo "📊 Checking container status..."
docker-compose ps

# Start ngrok tunnel for frontend (port 3000)
echo "🚀 Starting ngrok tunnel for frontend (port 3000)..."
echo "📱 Your public URL will be displayed below:"
echo "🔗 Share this URL with your colleagues to test the system"
echo ""

# Start ngrok in background and capture the URL
ngrok http 3000 --log=stdout | while read line; do
    if echo "$line" | grep -q "started tunnel"; then
        echo "✅ Tunnel started successfully!"
    elif echo "$line" | grep -q "url=https://"; then
        url=$(echo "$line" | grep -o 'https://[^[:space:]]*')
        echo ""
        echo "🎉 PUBLIC URL READY:"
        echo "🔗 $url"
        echo ""
        echo "📋 Share this URL with your colleagues:"
        echo "   $url"
        echo ""
        echo "🔐 Login credentials:"
        echo "   Email: test@test.com"
        echo "   Password: test123"
        echo ""
        echo "⏹️  Press Ctrl+C to stop the tunnel"
        echo ""
    fi
done
