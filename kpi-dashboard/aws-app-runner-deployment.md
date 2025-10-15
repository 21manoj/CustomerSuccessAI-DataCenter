# AWS App Runner Deployment Guide

## Overview
AWS App Runner is the simplest way to deploy containerized applications on AWS. Perfect for MVP deployment with automatic scaling and load balancing.

## Prerequisites
- AWS CLI configured
- Docker images built and pushed to ECR
- Domain name (optional)

## Step 1: Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository --repository-name kpi-dashboard-backend --region us-east-1
aws ecr create-repository --repository-name kpi-dashboard-frontend --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
```

## Step 2: Build and Push Docker Images

```bash
# Build and tag images
docker build -f backend/Dockerfile.production -t kpi-dashboard-backend .
docker build -f Dockerfile.production -t kpi-dashboard-frontend .

# Tag for ECR
docker tag kpi-dashboard-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-backend:latest
docker tag kpi-dashboard-frontend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-frontend:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-frontend:latest
```

## Step 3: Create App Runner Services

### Backend Service
```yaml
# apprunner-backend.yaml
version: 1.0
runtime: docker
build:
  commands:
    build:
      - echo "No build commands needed"
run:
  runtime-version: latest
  command: python app.py
  network:
    port: 5059
    env: PORT
  env:
    - name: FLASK_ENV
      value: production
    - name: SQLALCHEMY_DATABASE_URI
      value: sqlite:///instance/kpi_dashboard.db
    - name: OPENAI_API_KEY
      value: "your-openai-api-key"
```

### Frontend Service
```yaml
# apprunner-frontend.yaml
version: 1.0
runtime: docker
build:
  commands:
    build:
      - echo "No build commands needed"
run:
  runtime-version: latest
  command: nginx -g "daemon off;"
  network:
    port: 80
    env: PORT
```

## Step 4: Deploy via AWS Console

1. Go to AWS App Runner console
2. Create service for backend:
   - Source: Container registry (ECR)
   - Image: kpi-dashboard-backend:latest
   - Port: 5059
   - Environment variables as above

3. Create service for frontend:
   - Source: Container registry (ECR)
   - Image: kpi-dashboard-frontend:latest
   - Port: 80

## Step 5: Configure Custom Domain (Optional)

1. In App Runner console, go to Custom domains
2. Add your domain
3. Update DNS records as instructed

## Cost Estimate
- Backend: ~$25-50/month
- Frontend: ~$25-50/month
- Total: ~$50-100/month

## Benefits
- ✅ Zero infrastructure management
- ✅ Automatic scaling
- ✅ Built-in load balancing
- ✅ HTTPS by default
- ✅ Easy deployment
