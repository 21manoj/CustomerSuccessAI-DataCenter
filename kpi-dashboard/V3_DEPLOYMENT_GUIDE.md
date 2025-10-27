# V3 Deployment Guide

## Quick Start

Simply run the automated deployment script:

```bash
./deploy-v3-final.sh
```

This script automatically handles all deployment steps.

## Manual Deployment Steps

If you need to deploy manually or troubleshoot:

### 1. Build Frontend Locally

```bash
npm run build
```

This creates the `build/` directory with production-ready files.

### 2. Package Application

```bash
tar -czf kpi-dashboard-v3-final.tar.gz \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='.git' \
    --exclude='qdrant_storage*' \
    --exclude='*.tar.gz' \
    .
```

### 3. Upload to AWS

```bash
scp -i kpi-dashboard-key.pem kpi-dashboard-v3-final.tar.gz ec2-user@3.84.178.121:/home/ec2-user/
```

### 4. Deploy on AWS

SSH into the server and run:

```bash
# Clean up old deployment
sudo rm -rf /home/ec2-user/kpi-dashboard-v3

# Extract new package
mkdir -p /home/ec2-user/kpi-dashboard-v3
tar -xzf /home/ec2-user/kpi-dashboard-v3-final.tar.gz -C /home/ec2-user/kpi-dashboard-v3

# Copy database (if exists)
cp /home/ec2-user/backend/instance/kpi_dashboard.db /home/ec2-user/kpi-dashboard-v3/instance/ 2>/dev/null || true

# Restart containers
cd /home/ec2-user/kpi-dashboard-v3
docker-compose -f docker-compose.local-v3.yml restart backend-v3 frontend-v3
```

### 5. Verify Deployment

```bash
# Check backend health
curl https://customervaluesystem.triadpartners.ai/api/health

# Check accounts with health scores
curl https://customervaluesystem.triadpartners.ai/api/accounts -H "X-Customer-ID: 1"

# Check frontend
curl https://customervaluesystem.triadpartners.ai/
```

## Key Features Deployed in V3

### ✅ Health Scores
- Calculated on-demand from KPIs
- Included in `/api/accounts` response
- Included in RAG context automatically

### ✅ RAG with Health Scores
- `direct_rag_api.py` includes health scores in context
- No knowledge base rebuild required
- Always uses latest health scores

### ✅ Frontend
- React SPA served via Nginx
- Properly proxied to backend
- All features operational

## Troubleshooting

### 403 Forbidden on Frontend
If frontend returns 403, rebuild and re-upload:
```bash
npm run build
scp -r build/* ec2-user@3.84.178.121:/home/ec2-user/kpi-dashboard-v3/build/
ssh ec2-user@3.84.178.121 "cd /home/ec2-user/kpi-dashboard-v3 && docker restart kpi-dashboard-v3-frontend-v3-1"
```

### Health Scores Not Showing
Check that these files are deployed:
- `backend/kpi_api.py` (includes health score calculation)
- `backend/direct_rag_api.py` (includes health scores in context)
- `backend/playbook_recommendations_api.py` (health score calculation function)

### Backend Not Responding
```bash
# Check container status
ssh ec2-user@3.84.178.121 "docker ps | grep backend"

# Check logs
ssh ec2-user@3.84.178.121 "docker logs kpi-dashboard-v3-backend-v3-1"

# Restart if needed
ssh ec2-user@3.84.178.121 "cd /home/ec2-user/kpi-dashboard-v3 && docker restart kpi-dashboard-v3-backend-v3-1"
```

## Files Modified for Health Scores

1. **backend/kpi_api.py** (lines 72-113)
   - Added health score calculation to `/api/accounts` endpoint
   - Includes `HealthTrend` lookup and fallback calculation

2. **backend/direct_rag_api.py** (lines 197-220)
   - Added health scores to RAG context data
   - Automatically includes scores for all accounts

3. **backend/app_v3_minimal.py** (lines 110-164)
   - Alternative accounts endpoint with health scores

## Production URL

**https://customervaluesystem.triadpartners.ai**

## Ports

- Backend: 5059 (internal), exposed via Nginx
- Frontend: 3003 (internal), exposed via Nginx on 443 (HTTPS)

## Docker Containers

- `kpi-dashboard-v3-backend-v3-1` - Backend API
- `kpi-dashboard-v3-frontend-v3-1` - Frontend Nginx

## Next Deployment

For future deployments, all these steps are automated in `deploy-v3-final.sh`. Simply run it and the script will:
1. Build frontend
2. Package application
3. Upload to AWS
4. Deploy and restart containers
5. Verify deployment

No manual intervention needed! 🚀
