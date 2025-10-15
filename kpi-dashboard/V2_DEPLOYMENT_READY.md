# KPI Dashboard V2 - Ready for AWS Deployment 🚀

## Package Information

**File:** `kpi-dashboard-v2-production.tar.gz`  
**Size:** 2.5 MB  
**Created:** October 14, 2025  
**Status:** ✅ READY FOR DEPLOYMENT

---

## What's Included in V2

### **Complete Application**
- ✅ Backend: 120+ Python files, 50+ API endpoints
- ✅ Frontend: Modern React UI with 10+ components
- ✅ Database: 18 tables with sample data (2 customers)
- ✅ Migrations: 3 new migration scripts
- ✅ Documentation: 25+ markdown files

### **Key Features**
1. **Intelligent Query Routing** - Analytics + RAG
2. **5 Complete Playbooks** - 49 total steps
3. **Playbook-Enhanced RAG** - Contextual AI responses
4. **Multi-Tenant SaaS** - 2 customers, complete isolation
5. **Database Persistence** - All data survives restarts
6. **Modern UI** - Gradients, animations, logo support
7. **Fivetran Integration** - Ready for Salesforce + ServiceNow
8. **Self-Registration** - Customer signup API

---

## Quick Deployment Options

### **Option 1: AWS App Runner** (Recommended)

**Pros:**
- Fully managed, auto-scaling
- Simple deployment
- Built-in load balancing
- HTTPS automatic

**Command:**
```bash
# Upload package
aws s3 cp kpi-dashboard-v2-production.tar.gz s3://your-bucket/v2/

# Deploy (use existing apprunner config)
aws apprunner update-service \
  --service-arn your-service-arn \
  --source-configuration file://apprunner-v2.yaml
```

**Time:** ~10 minutes  
**Cost:** ~$25/month

### **Option 2: AWS ECS Fargate**

**Pros:**
- More control
- VPC networking
- Better for large scale

**Commands:**
```bash
# Build and push Docker image
docker build -t kpi-dashboard:v2 .
docker tag kpi-dashboard:v2 your-ecr-repo/kpi-dashboard:v2
docker push your-ecr-repo/kpi-dashboard:v2

# Update ECS service
aws ecs update-service \
  --cluster kpi-dashboard-cluster \
  --service kpi-dashboard-service \
  --task-definition kpi-dashboard-v2
```

**Time:** ~15 minutes  
**Cost:** ~$30-50/month

### **Option 3: AWS EC2**

**Pros:**
- Full control
- SSH access
- Custom configuration

**Commands:**
```bash
# Upload package to EC2
scp kpi-dashboard-v2-production.tar.gz ec2-user@your-ec2-ip:/home/ec2-user/

# SSH and deploy
ssh ec2-user@your-ec2-ip
tar -xzf kpi-dashboard-v2-production.tar.gz
cd kpi-dashboard
./deploy-v2-ec2.sh
```

**Time:** ~20 minutes  
**Cost:** ~$20-40/month (t3.medium)

---

## Pre-Deployment Checklist

### **Environment Setup**
- [ ] AWS Account configured
- [ ] AWS CLI installed and configured
- [ ] S3 bucket created for backups
- [ ] CloudWatch logs enabled
- [ ] Secrets Manager configured

### **API Keys & Credentials**
- [ ] OpenAI API key in AWS Secrets Manager
- [ ] Anthropic API key (optional)
- [ ] Fivetran API credentials (if using)
- [ ] Salesforce credentials (if using)
- [ ] ServiceNow credentials (if using)

### **Database**
- [ ] Decide: SQLite vs PostgreSQL
- [ ] If PostgreSQL: RDS instance created
- [ ] Database migrations tested locally
- [ ] Backup strategy configured

### **Domain & SSL**
- [ ] Domain name configured
- [ ] SSL certificate in ACM
- [ ] CloudFront distribution (if using)
- [ ] Route 53 DNS records

---

## Deployment Steps (When Ready)

### Step 1: Prepare AWS Environment

```bash
# Create S3 bucket for deployments
aws s3 mb s3://kpi-dashboard-v2-deployments

# Create S3 bucket for backups
aws s3 mb s3://kpi-dashboard-v2-backups

# Create CloudWatch log group
aws logs create-log-group --log-group-name /aws/kpi-dashboard-v2
```

### Step 2: Upload Deployment Package

```bash
# Upload V2 package
aws s3 cp kpi-dashboard-v2-production.tar.gz \
  s3://kpi-dashboard-v2-deployments/v2.0.0/

# Verify upload
aws s3 ls s3://kpi-dashboard-v2-deployments/v2.0.0/
```

### Step 3: Deploy to App Runner

```bash
# Create or update service
aws apprunner create-service \
  --cli-input-json file://apprunner-v2-config.json

# Or update existing
aws apprunner update-service \
  --service-arn <your-service-arn> \
  --source-configuration file://apprunner-v2.yaml
```

### Step 4: Run Migrations

```bash
# SSH to instance or run via App Runner console
python backend/migrations/add_playbook_executions_table.py
python backend/migrations/add_playbook_reports_table.py
```

### Step 5: Verify Deployment

```bash
# Check health
curl https://your-domain.com/

# Test login
curl -X POST https://your-domain.com/api/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "test@test.com", "password": "test123"}'

# Test accounts
curl https://your-domain.com/api/accounts -H 'X-Customer-ID: 1'
```

---

## Post-Deployment Configuration

### 1. Update Frontend API URL

If deploying to custom domain, update:

```tsx
// src/config.ts (create if needed)
export const API_BASE_URL = process.env.REACT_APP_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? 'https://api.your-domain.com' 
    : 'http://localhost:5059');
```

### 2. Configure CORS

```python
# backend/app.py
CORS(app, origins=[
    'https://your-domain.com',
    'https://www.your-domain.com'
])
```

### 3. Set Up Monitoring

```bash
# Enable CloudWatch metrics
aws cloudwatch put-metric-alarm \
  --alarm-name kpi-dashboard-v2-high-error-rate \
  --metric-name Errors \
  --threshold 10
```

---

## V2 Features Summary

### **For Customers:**
✅ Self-service registration  
✅ Upload KPI data (Excel)  
✅ View dashboards and analytics  
✅ Execute playbooks  
✅ Query AI insights  
✅ View comprehensive reports  
✅ Configure settings  

### **For Admins:**
✅ Multi-customer management  
✅ Fivetran integration setup  
✅ Data warehouse configuration  
✅ Monitoring and logs  
✅ Backup management  

---

## V2 Data Migration

### Existing Customers (V1 → V2):

**No action needed!** V2 is backward compatible.

Existing data automatically available:
- ✅ All accounts
- ✅ All KPIs
- ✅ All uploads
- ✅ All settings

New V2 features become immediately available:
- ✅ Playbooks
- ✅ Enhanced RAG
- ✅ Query routing
- ✅ Reports

---

## V2 Support & Troubleshooting

### Common Issues

**Issue 1: Database migration fails**
```bash
# Solution: Check database permissions
ls -l instance/kpi_dashboard.db
chmod 664 instance/kpi_dashboard.db
```

**Issue 2: OpenAI API errors**
```bash
# Solution: Check API key in Secrets Manager
aws secretsmanager get-secret-value --secret-id openai-api-key
```

**Issue 3: Playbooks not loading**
```bash
# Solution: Check migrations ran
python -c "from app import app, db; from models import PlaybookExecution; 
app.app_context().push(); print(PlaybookExecution.query.count())"
```

---

## V2 Rollout Strategy

### Phase 1: Staging (Recommended)
1. Deploy V2 to staging environment
2. Test with 1-2 customers
3. Run for 1 week
4. Monitor metrics and logs

### Phase 2: Production (50%)
1. Deploy V2 to production
2. Route 50% of traffic to V2
3. Monitor for 3 days
4. Compare V1 vs V2 metrics

### Phase 3: Production (100%)
1. Route 100% traffic to V2
2. Monitor for 1 week
3. Decommission V1
4. Celebrate! 🎉

---

## V2 Success Metrics

### Track These After Deployment:

**Performance:**
- [ ] API response time < 200ms (avg)
- [ ] Page load time < 2s
- [ ] Query cache hit rate > 50%
- [ ] Error rate < 0.1%

**Adoption:**
- [ ] Playbooks executed per week
- [ ] Reports generated per customer
- [ ] RAG queries with playbook context
- [ ] Customer self-registrations

**Cost:**
- [ ] RAG query costs reduced (via caching)
- [ ] Infrastructure costs within budget
- [ ] Total cost per customer

---

## Conclusion

✅ **V2 Package Created:** `kpi-dashboard-v2-production.tar.gz` (2.5 MB)  
✅ **All Features Tested:** Locally verified  
✅ **Documentation Complete:** 25+ guides  
✅ **Deployment Scripts Ready:** App Runner, ECS, EC2  
✅ **Database Migrations Ready:** 3 scripts prepared  
✅ **Multi-Tenant Ready:** 2 customers configured  
✅ **Backward Compatible:** No breaking changes  

---

**V2 is ready for AWS deployment whenever you are!** 🎉

**Next Steps:**
1. Review V2_DEPLOYMENT_PACKAGE.md
2. Choose deployment option (App Runner recommended)
3. Configure AWS environment
4. Run deployment script
5. Verify functionality
6. Go live!

**Package Location:**
```
/Users/manojgupta/kpi-dashboard/kpi-dashboard-v2-production.tar.gz
```

**Ready to deploy to AWS!** 🚀☁️

