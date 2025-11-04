#!/bin/bash
set -e

echo "🚀 Deploying V3 to Production..."

# Extract the package
cd /home/ec2-user
rm -rf kpi-dashboard-v3
mkdir -p kpi-dashboard-v3
tar -xzf kpi-dashboard-v3.tar.gz -C kpi-dashboard-v3
cd kpi-dashboard-v3

# Copy the existing database from V2 (if exists)
if [ -f ../instance/kpi_dashboard.db ]; then
    echo "📊 Copying existing database..."
    cp ../instance/kpi_dashboard.db instance/
else
    echo "⚠️  No existing database found, using fresh one"
fi

# Build and start containers
echo "🔨 Building Docker images..."
docker-compose -f docker-compose.local-v3.yml build --no-cache

echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.local-v3.yml down

echo "🚀 Starting V3 containers..."
docker-compose -f docker-compose.local-v3.yml up -d

echo "⏳ Waiting for containers to start..."
sleep 10

echo "✅ Deployment complete!"
echo "📊 Backend: http://3.84.178.121:5059"
echo "🌐 Frontend: http://3.84.178.121:3003"
echo "🔗 Production: https://customervaluesystem.triadpartners.ai"

# Check status
echo ""
echo "📊 Container Status:"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

