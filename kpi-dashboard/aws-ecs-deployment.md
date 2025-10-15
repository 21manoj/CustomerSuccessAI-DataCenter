# AWS ECS with Fargate Deployment Guide

## Overview
ECS Fargate provides serverless container orchestration with full control over networking and security. Best for production workloads.

## Prerequisites
- AWS CLI configured
- Docker images in ECR
- VPC and subnets configured

## Step 1: Create ECR Repositories

```bash
# Create ECR repositories
aws ecr create-repository --repository-name kpi-dashboard-backend --region us-east-1
aws ecr create-repository --repository-name kpi-dashboard-frontend --region us-east-1

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
```

## Step 2: Build and Push Images

```bash
# Build and push backend
docker build -f backend/Dockerfile.production -t kpi-dashboard-backend .
docker tag kpi-dashboard-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-backend:latest

# Build and push frontend
docker build -f Dockerfile.production -t kpi-dashboard-frontend .
docker tag kpi-dashboard-frontend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-frontend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-frontend:latest
```

## Step 3: Create Task Definitions

### Backend Task Definition
```json
{
  "family": "kpi-dashboard-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-backend:latest",
      "portMappings": [
        {
          "containerPort": 5059,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "FLASK_ENV",
          "value": "production"
        },
        {
          "name": "SQLALCHEMY_DATABASE_URI",
          "value": "sqlite:///instance/kpi_dashboard.db"
        },
        {
          "name": "OPENAI_API_KEY",
          "value": "your-openai-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/kpi-dashboard-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Frontend Task Definition
```json
{
  "family": "kpi-dashboard-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-frontend:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/kpi-dashboard-frontend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Step 4: Create ECS Cluster

```bash
# Create cluster
aws ecs create-cluster --cluster-name kpi-dashboard-cluster

# Create log groups
aws logs create-log-group --log-group-name /ecs/kpi-dashboard-backend
aws logs create-log-group --log-group-name /ecs/kpi-dashboard-frontend
```

## Step 5: Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name kpi-dashboard-alb \
  --subnets subnet-12345 subnet-67890 \
  --security-groups sg-12345

# Create target groups
aws elbv2 create-target-group \
  --name kpi-backend-tg \
  --protocol HTTP \
  --port 5059 \
  --vpc-id vpc-12345 \
  --target-type ip

aws elbv2 create-target-group \
  --name kpi-frontend-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-12345 \
  --target-type ip
```

## Step 6: Create ECS Services

```bash
# Create backend service
aws ecs create-service \
  --cluster kpi-dashboard-cluster \
  --service-name kpi-backend-service \
  --task-definition kpi-dashboard-backend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-12345],assignPublicIp=ENABLED}"

# Create frontend service
aws ecs create-service \
  --cluster kpi-dashboard-cluster \
  --service-name kpi-frontend-service \
  --task-definition kpi-dashboard-frontend:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

## Step 7: Configure Load Balancer Rules

```bash
# Create listener rules
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:<account-id>:loadbalancer/app/kpi-dashboard-alb/12345 \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<account-id>:targetgroup/kpi-frontend-tg/12345

# Add API path rule
aws elbv2 create-rule \
  --listener-arn arn:aws:elasticloadbalancing:us-east-1:<account-id>:listener/app/kpi-dashboard-alb/12345/56789 \
  --priority 100 \
  --conditions Field=path-pattern,Values=/api/* \
  --actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:<account-id>:targetgroup/kpi-backend-tg/12345
```

## Cost Estimate
- ECS Fargate: ~$30-60/month per service
- ALB: ~$20/month
- ECR: ~$5/month
- Total: ~$85-145/month

## Benefits
- ✅ Full control over infrastructure
- ✅ Auto-scaling based on metrics
- ✅ Health checks and rolling updates
- ✅ Integration with AWS services
- ✅ Production-ready security
