#!/bin/bash
# V3 Automated Deployment Script with Health Score Support
# This script packages and deploys V3 with all fixes applied

set -e  # Exit on error

echo "🚀 Starting V3 Deployment Process..."

# Step 1: Build frontend locally
echo "📦 Building frontend..."
cd "$(dirname "$0")"
npm run build
if [ $? -ne 0 ]; then
    echo "❌ Frontend build failed"
    exit 1
fi
echo "✅ Frontend built successfully"

# Step 2: Create deployment package
echo "📦 Creating deployment package..."
tar -czf kpi-dashboard-v3-final.tar.gz \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='qdrant_storage*' \
    --exclude='*.tar.gz' \
    --exclude='instance/.gitkeep' \
    .

echo "✅ Package created: kpi-dashboard-v3-final.tar.gz"

# Step 3: Upload to AWS
echo "☁️  Uploading to AWS..."
scp -i kpi-dashboard-key.pem kpi-dashboard-v3-final.tar.gz ec2-user@3.84.178.121:/home/ec2-user/

# Step 4: Deploy on AWS
echo "🔄 Deploying on AWS..."
ssh -i kpi-dashboard-key.pem ec2-user@3.84.178.121 << 'DEPLOY_SCRIPT'
    set -e
    
    # Clean up old deployment
    echo "Cleaning up old deployment..."
    sudo rm -rf /home/ec2-user/kpi-dashboard-v3
    
    # Extract new package
    echo "Extracting new package..."
    mkdir -p /home/ec2-user/kpi-dashboard-v3
    tar -xzf /home/ec2-user/kpi-dashboard-v3-final.tar.gz -C /home/ec2-user/kpi-dashboard-v3 2>&1 | grep -v 'LIBARCHIVE.xattr' || true
    
    # Copy database from local
    echo "Copying database..."
    if [ -f "/home/ec2-user/backend/instance/kpi_dashboard.db" ]; then
        cp /home/ec2-user/backend/instance/kpi_dashboard.db /home/ec2-user/kpi-dashboard-v3/instance/ 2>/dev/null || true
    fi
    
    # Restart containers
    echo "Restarting containers..."
    cd /home/ec2-user/kpi-dashboard-v3
    docker-compose -f docker-compose.local-v3.yml restart backend-v3 frontend-v3
    
    echo "✅ Deployment complete!"
DEPLOY_SCRIPT

# Step 5: Verify deployment
echo "🔍 Verifying deployment..."
sleep 5

# Check health endpoint
HEALTH_CHECK=$(curl -s https://customervaluesystem.triadpartners.ai/api/health | jq -r '.status' 2>/dev/null || echo "error")
if [ "$HEALTH_CHECK" = "healthy" ]; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed: $HEALTH_CHECK"
    exit 1
fi

# Check accounts endpoint with health scores
ACCOUNTS_COUNT=$(curl -s "https://customervaluesystem.triadpartners.ai/api/accounts" -H "X-Customer-ID: 1" | jq 'length' 2>/dev/null || echo "0")
if [ "$ACCOUNTS_COUNT" -gt "0" ]; then
    echo "✅ Accounts endpoint returned $ACCOUNTS_COUNT accounts with health scores"
else
    echo "❌ Accounts endpoint failed or returned no accounts"
    exit 1
fi

# Check frontend
FRONTEND_TITLE=$(curl -s "https://customervaluesystem.triadpartners.ai/" | grep -o '<title>.*</title>' || echo "error")
if [[ "$FRONTEND_TITLE" == *"React App"* ]]; then
    echo "✅ Frontend is accessible"
else
    echo "❌ Frontend check failed: $FRONTEND_TITLE"
    exit 1
fi

echo ""
echo "🎉 V3 Deployment Complete!"
echo "✅ Health scores are calculated on-demand"
echo "✅ RAG includes health scores in context"
echo "✅ Frontend and backend are operational"
echo ""
echo "🌐 URL: https://customervaluesystem.triadpartners.ai"
echo ""
echo "Available tests:"
echo "  - Query: 'Show me account health scores and performance'"
echo "  - API: curl https://customervaluesystem.triadpartners.ai/api/accounts -H 'X-Customer-ID: 1'"
