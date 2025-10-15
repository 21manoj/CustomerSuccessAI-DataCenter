#!/bin/bash

# AWS Deployment Script for KPI Dashboard
set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BACKEND_REPO="kpi-dashboard-backend"
ECR_FRONTEND_REPO="kpi-dashboard-frontend"
CLUSTER_NAME="kpi-dashboard-cluster"

echo "🚀 Starting AWS deployment for KPI Dashboard..."
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists aws; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

if ! command_exists docker; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Step 1: Create ECR repositories
echo "📦 Creating ECR repositories..."

aws ecr create-repository --repository-name $ECR_BACKEND_REPO --region $AWS_REGION 2>/dev/null || echo "Backend repository already exists"
aws ecr create-repository --repository-name $ECR_FRONTEND_REPO --region $AWS_REGION 2>/dev/null || echo "Frontend repository already exists"

echo "✅ ECR repositories ready"

# Step 2: Login to ECR
echo "🔐 Logging in to ECR..."

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "✅ ECR login successful"

# Step 3: Build and push images
echo "🔨 Building and pushing Docker images..."

# Build backend
echo "Building backend image..."
docker build -f backend/Dockerfile.production -t $ECR_BACKEND_REPO ./backend
docker tag $ECR_BACKEND_REPO:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_BACKEND_REPO:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_BACKEND_REPO:latest

# Build frontend
echo "Building frontend image..."
docker build -f Dockerfile.production -t $ECR_FRONTEND_REPO .
docker tag $ECR_FRONTEND_REPO:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_FRONTEND_REPO:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_FRONTEND_REPO:latest

echo "✅ Images pushed to ECR"

# Step 4: Deploy to App Runner (simplest option)
echo "🚀 Deploying to AWS App Runner..."

# Create App Runner service configuration
cat > apprunner-backend.yaml << EOF
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
      value: "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"
EOF

cat > apprunner-frontend.yaml << EOF
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
EOF

echo "📋 App Runner configuration files created:"
echo "   - apprunner-backend.yaml"
echo "   - apprunner-frontend.yaml"

echo ""
echo "🎉 Deployment preparation complete!"
echo ""
echo "Next steps:"
echo "1. Go to AWS App Runner console: https://console.aws.amazon.com/apprunner/"
echo "2. Create service for backend using: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_BACKEND_REPO:latest"
echo "3. Create service for frontend using: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_FRONTEND_REPO:latest"
echo "4. Configure custom domain (optional)"
echo ""
echo "Alternative deployment options:"
echo "- ECS Fargate: See aws-ecs-deployment.md"
echo "- EKS: See aws-eks-deployment.md"
echo ""
echo "💰 Estimated monthly cost: $50-100 (App Runner)"
