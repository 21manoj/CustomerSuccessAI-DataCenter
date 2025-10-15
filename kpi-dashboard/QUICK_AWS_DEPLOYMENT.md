# Quick AWS Deployment Guide

## 🚀 **Fastest Path to Production**

### **Step 1: Prerequisites (5 minutes)**
```bash
# Install AWS CLI (if not installed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS CLI
aws configure
# Enter your Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)
```

### **Step 2: Run Deployment Script (10 minutes)**
```bash
# Make script executable and run
chmod +x deploy-to-aws.sh
./deploy-to-aws.sh
```

### **Step 3: Deploy via AWS Console (15 minutes)**

#### **Backend Service:**
1. Go to [AWS App Runner Console](https://console.aws.amazon.com/apprunner/)
2. Click "Create service"
3. Choose "Container registry"
4. Select your ECR repository: `kpi-dashboard-backend`
5. Service name: `kpi-backend`
6. Port: `5059`
7. Environment variables:
   - `FLASK_ENV=production`
   - `SQLALCHEMY_DATABASE_URI=sqlite:///instance/kpi_dashboard.db`
   - `OPENAI_API_KEY=your-key-here`
8. Click "Create & deploy"

#### **Frontend Service:**
1. Create another service
2. Select ECR repository: `kpi-dashboard-frontend`
3. Service name: `kpi-frontend`
4. Port: `80`
5. Click "Create & deploy"

### **Step 4: Configure Custom Domain (Optional)**
1. In App Runner console, go to "Custom domains"
2. Add your domain name
3. Update DNS records as instructed

## 🎯 **Alternative: One-Click ECS Deployment**

```bash
# Deploy to ECS Fargate
aws ecs create-cluster --cluster-name kpi-dashboard
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-service --cluster kpi-dashboard --service-name kpi-service --task-definition kpi-dashboard:1 --desired-count 2
```

## 📊 **Cost Comparison**

| Option | Monthly Cost | Complexity | Best For |
|--------|-------------|------------|----------|
| App Runner | $50-100 | Low | MVP, Quick deployment |
| ECS Fargate | $85-145 | Medium | Production, Scaling |
| EKS | $152-212 | High | Enterprise, Multi-tenant |

## 🔧 **Troubleshooting**

### **Common Issues:**
1. **ECR Login Failed**: Run `aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com`
2. **Permission Denied**: Ensure your AWS user has ECR, App Runner, and ECS permissions
3. **Image Not Found**: Verify the image was pushed to ECR successfully

### **Health Checks:**
```bash
# Check backend health
curl https://your-backend-url.amazonaws.com/api/accounts -H "X-Customer-ID: 6"

# Check frontend
curl https://your-frontend-url.amazonaws.com/
```

## 🚀 **Production Checklist**

- [ ] SSL/TLS certificates configured
- [ ] Custom domain set up
- [ ] Environment variables secured
- [ ] Database migrated to RDS
- [ ] Monitoring and logging enabled
- [ ] Backup strategy implemented
- [ ] Security groups configured
- [ ] Load balancer health checks passing

## 📞 **Support**

- AWS App Runner: [Documentation](https://docs.aws.amazon.com/apprunner/)
- ECS Fargate: [Documentation](https://docs.aws.amazon.com/ecs/)
- EKS: [Documentation](https://docs.aws.amazon.com/eks/)

## 🎉 **You're Ready!**

Your KPI Dashboard is now running on AWS with:
- ✅ Auto-scaling
- ✅ Load balancing
- ✅ HTTPS security
- ✅ High availability
- ✅ Managed infrastructure
