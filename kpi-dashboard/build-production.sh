#!/bin/bash

# Production Build Script for KPI Dashboard
set -e

echo "🚀 Building KPI Dashboard for Production..."

# Stop any running containers
echo "📦 Stopping existing containers..."
docker-compose -f docker-compose.production.yml down || true

# Build and start production containers
echo "🔨 Building production images..."
docker-compose -f docker-compose.production.yml build --no-cache

echo "🚀 Starting production containers..."
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Test the services
echo "🧪 Testing services..."

# Test backend
echo "Testing backend API..."
if curl -f -H "X-Customer-ID: 6" http://localhost:5059/api/accounts > /dev/null 2>&1; then
    echo "✅ Backend API is healthy"
else
    echo "❌ Backend API is not responding"
    exit 1
fi

# Test frontend
echo "Testing frontend..."
if curl -f http://localhost/ > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "❌ Frontend is not responding"
    exit 1
fi

# Test data endpoints
echo "Testing data endpoints..."
ACCOUNTS=$(curl -s -H "X-Customer-ID: 6" http://localhost:5059/api/accounts | jq '. | length' 2>/dev/null || echo "0")
KPIS=$(curl -s -H "X-Customer-ID: 6" http://localhost:5059/api/kpis/customer/all | jq '. | length' 2>/dev/null || echo "0")
RANGES=$(curl -s -H "X-Customer-ID: 6" http://localhost:5059/api/reference-ranges | jq '.reference_ranges | length' 2>/dev/null || echo "0")

echo "📊 Data Summary:"
echo "   Accounts: $ACCOUNTS"
echo "   KPIs: $KPIS"
echo "   Reference Ranges: $RANGES"

if [ "$ACCOUNTS" -gt 0 ] && [ "$KPIS" -gt 0 ] && [ "$RANGES" -gt 0 ]; then
    echo "✅ All data endpoints are working"
else
    echo "❌ Some data endpoints are not working"
    exit 1
fi

echo "🎉 Production build completed successfully!"
echo "🌐 Frontend: http://localhost"
echo "🔧 Backend API: http://localhost:5059"
echo "📊 Health Check: http://localhost:5059/api/health"
