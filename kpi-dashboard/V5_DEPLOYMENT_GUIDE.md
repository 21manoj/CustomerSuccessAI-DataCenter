# KPI Dashboard V5 - Deployment Guide

## Version 5.0.0 - Release Notes

**Release Date:** December 2024  
**Status:** Ready for AWS Deployment  
**Environment:** Production-ready

---

## 🎯 What's New in V5

### **Housekeeping & Cleanup**
- ✅ Removed future implementation placeholder files
- ✅ Streamlined deployment process
- ✅ Improved build and test scripts
- ✅ Enhanced error handling and validation
- ✅ Better documentation and organization

### **Deployment Improvements**
- ✅ Simplified docker-compose configuration
- ✅ Automated local build and test process
- ✅ Enhanced AWS deployment script
- ✅ Better health checks and monitoring
- ✅ Improved error messages and logging

### **Latest Features Included**
- ✅ **Playbook Support**: Complete playbook system with triggers, execution, reports, and recommendations
  - Playbook triggers API
  - Playbook execution API
  - Playbook reports API
  - Playbook recommendations API
  - 5 system playbooks: VoC Sprint, Activation Blitz, SLA Stabilizer, Renewal Safeguard, Expansion Timing

- ✅ **Multi-Product KPI Support**: Full support for product-level KPI tracking
  - Product dimension tracking (product_id)
  - Product-level health scores
  - Account and product-level KPI aggregation
  - Product-specific analytics

- ✅ **Enhanced Customer Profile Upload**: Advanced upload capabilities
  - Enhanced upload API with format detection
  - Multiple file format support (Excel, CSV)
  - Automatic format validation
  - Customer profile metadata upload
  - Event-driven RAG rebuilds

- ✅ **Enhanced RAG System**: Advanced AI capabilities
  - Enhanced RAG OpenAI API
  - Direct RAG API
  - Governance RAG API
  - Conversation history support
  - Playbook-enhanced insights

- ✅ **Customer Performance Summary**: Comprehensive performance tracking
  - Customer performance summary API
  - Account health trends
  - Revenue intelligence
  - Risk assessment

- ✅ **Data Quality & Management**: Advanced data handling
  - Data quality API
  - Export API
  - Workflow configuration API
  - Activity logging

---

## 📋 Prerequisites

### **Local Development**
- Node.js 18+ installed
- Python 3.11+ installed
- Docker and Docker Compose installed
- Git installed

### **AWS Deployment**
- AWS EC2 instance running
- SSH key pair configured
- Security groups configured
- Docker installed on EC2 instance

---

## 🚀 Quick Start

### **1. Local Build and Test**

First, build and test the application locally:

```bash
./build-and-test-v5.sh
```

This script will:
1. ✅ Check all prerequisites
2. ✅ Install dependencies
3. ✅ Build the frontend
4. ✅ Build Docker images
5. ✅ Start services
6. ✅ Run health checks

**Expected Output:**
- Backend: http://localhost:5059
- Frontend: http://localhost:3000

### **2. AWS Deployment**

Once local testing passes, deploy to AWS:

```bash
# Set AWS configuration (optional)
export AWS_EC2_IP=3.84.178.121
export AWS_KEY_FILE=kpi-dashboard-key.pem
export AWS_USER=ec2-user

# Deploy
./deploy-v5.sh
```

---

## 📦 Deployment Package Contents

The V5 deployment package includes:

- ✅ Complete application code
- ✅ Production build (frontend)
- ✅ Docker configuration files
- ✅ Database (if exists locally)
- ✅ Configuration templates
- ✅ Documentation

**Excluded from package:**
- `node_modules/` (installed on server)
- `venv/` (Python virtual environment)
- `.git/` (version control)
- `*.log` (log files)
- `*.pyc` (Python cache)
- `__pycache__/` (Python cache)

---

## 🐳 Docker Configuration

### **Services**

#### **Backend Service**
- **Container:** `kpi-dashboard-backend-v5`
- **Port:** `5059`
- **Health Check:** `/api/health`
- **Image:** Built from `backend/Dockerfile`

#### **Frontend Service**
- **Container:** `kpi-dashboard-frontend-v5`
- **Port:** `3000` (mapped to 80 in container)
- **Health Check:** HTTP 200 on `/`
- **Image:** Built from `Dockerfile.nginx`

### **Volumes**
- `./backend/instance` - Database persistence
- `./backend/uploads` - File uploads
- `./backend/qdrant_storage` - Vector database storage

### **Networks**
- `kpi-network-v5` - Bridge network for service communication

---

## 🔧 Configuration

### **Environment Variables**

Create `docker.env` file (or use existing):

```bash
# Flask Configuration
FLASK_APP=app_v3_minimal.py
FLASK_ENV=production
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5059

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///kpi_dashboard.db
SQLALCHEMY_TRACK_MODIFICATIONS=False

# OpenAI API Key (required for AI features)
OPENAI_API_KEY=your-openai-api-key

# RAG Configuration
RAG_TOP_K=10
RAG_SIMILARITY_THRESHOLD=0.3

# Qdrant Configuration (optional)
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### **AWS Security Groups**

Ensure these ports are open in your EC2 security group:

- **Port 5059** (Backend) - TCP from `0.0.0.0/0`
- **Port 3000** (Frontend) - TCP from `0.0.0.0/0`

Or configure nginx reverse proxy and only open ports 80/443.

---

## 🌐 Nginx Reverse Proxy (Optional)

For production deployments, configure nginx:

```nginx
# /etc/nginx/conf.d/kpi-dashboard-v5.conf
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:5059;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Cookie $http_cookie;
        proxy_pass_header Set-Cookie;
    }
}
```

Then reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔍 Monitoring & Troubleshooting

### **View Logs**

```bash
# All services
docker-compose -f docker-compose.v5.yml logs -f

# Backend only
docker-compose -f docker-compose.v5.yml logs -f backend

# Frontend only
docker-compose -f docker-compose.v5.yml logs -f frontend
```

### **Check Container Status**

```bash
docker-compose -f docker-compose.v5.yml ps
```

### **Health Checks**

```bash
# Backend health
curl http://localhost:5059/api/health

# Frontend health
curl http://localhost:3000
```

### **Restart Services**

```bash
# Restart all services
docker-compose -f docker-compose.v5.yml restart

# Restart specific service
docker-compose -f docker-compose.v5.yml restart backend
```

### **Stop Services**

```bash
docker-compose -f docker-compose.v5.yml down
```

### **Rebuild Services**

```bash
docker-compose -f docker-compose.v5.yml up -d --build
```

---

## 📊 Deployment Checklist

### **Pre-Deployment**
- [ ] Local build and test successful
- [ ] All tests passing
- [ ] Database backed up (if upgrading)
- [ ] Environment variables configured
- [ ] AWS credentials verified

### **Deployment**
- [ ] Deployment package created
- [ ] Package uploaded to AWS
- [ ] Services started successfully
- [ ] Health checks passing
- [ ] Database migrated (if needed)

### **Post-Deployment**
- [ ] Security groups configured
- [ ] Nginx configured (if using)
- [ ] SSL certificate installed (if using)
- [ ] DNS configured
- [ ] Monitoring set up
- [ ] Documentation updated

---

## 🔄 Upgrading from Previous Versions

### **From V4 to V5**

1. **Backup existing deployment:**
   ```bash
   # On AWS server
   cd /home/ec2-user/kpi-dashboard-v4
   cp backend/instance/kpi_dashboard.db backend/instance/kpi_dashboard.db.v4backup
   ```

2. **Deploy V5:**
   ```bash
   # On local machine
   ./deploy-v5.sh
   ```

3. **Verify migration:**
   - Check database integrity
   - Verify all accounts accessible
   - Test API endpoints
   - Test frontend functionality

---

## 🐛 Common Issues

### **Port Already in Use**
```bash
# Check what's using the port
sudo lsof -i :5059
sudo lsof -i :3000

# Stop conflicting services or change ports in docker-compose.v5.yml
```

### **Database Locked**
```bash
# Stop services
docker-compose -f docker-compose.v5.yml down

# Check database
sqlite3 backend/instance/kpi_dashboard.db ".tables"

# Restart services
docker-compose -f docker-compose.v5.yml up -d
```

### **Build Failures**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker-compose -f docker-compose.v5.yml build --no-cache
```

### **Permission Issues**
```bash
# Fix permissions
sudo chown -R $USER:$USER backend/instance
sudo chown -R $USER:$USER backend/uploads
```

---

## 📝 Version History

### **V5.0.0** (December 2024)
- Housekeeping and cleanup
- Improved deployment scripts
- Enhanced documentation
- Streamlined configuration

### **V4.0.0** (November 2024)
- Session-based authentication
- Performance improvements
- Customer Performance Summary panels
- Enhanced security

### **V3.0.0** (October 2024)
- Multi-tenant SaaS architecture
- Playbook system
- RAG enhancements
- Query routing

---

## 🆘 Support

For issues or questions:
1. Check logs: `docker-compose -f docker-compose.v5.yml logs`
2. Review this documentation
3. Check health endpoints
4. Verify configuration files

---

## ✅ V5 Ready for Deployment!

The V5 release is production-ready and includes all necessary improvements for a clean, maintainable deployment.

**Next Steps:**
1. Run `./build-and-test-v5.sh` locally
2. Verify all tests pass
3. Run `./deploy-v5.sh` for AWS deployment
4. Configure security groups and DNS
5. Monitor and verify deployment

---

**Deployment Guide Version:** 1.0  
**Last Updated:** December 2024

