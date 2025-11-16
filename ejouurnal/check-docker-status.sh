#!/bin/bash
# Quick script to check Docker container status

echo "🐳 DOCKER STATUS CHECK"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "📦 Containers:"
docker ps --filter "name=fulfillment" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "🏗️ Building/Exited:"
docker ps -a --filter "name=fulfillment" --filter "status=exited" --format "table {{.Names}}\t{{.Status}}"
echo ""

echo "🌐 Health Checks:"
echo -n "Backend (3005): "
curl -s http://localhost:3005/health 2>/dev/null && echo "✅ Healthy" || echo "❌ Not responding"
echo -n "Frontend (3006): "
curl -s http://localhost:3006/health 2>/dev/null && echo "✅ Healthy" || echo "❌ Not responding"
echo ""

echo "📊 Recent Logs:"
echo "--- Backend ---"
docker logs --tail 5 fulfillment-backend 2>/dev/null || echo "Container not started yet"
echo ""

