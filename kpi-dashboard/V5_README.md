# KPI Dashboard V5 - Quick Start

## 🚀 Quick Start

### Local Build and Test
```bash
./build-and-test-v5.sh
```

This will:
- ✅ Check prerequisites
- ✅ Build frontend
- ✅ Build Docker images
- ✅ Start services
- ✅ Run health checks

**Access:**
- Frontend: http://localhost:3000
- Backend: http://localhost:5059

### AWS Deployment
```bash
./deploy-v5.sh
```

---

## 📋 What's in V5

### **Housekeeping & Cleanup**
- ✅ Removed placeholder files
- ✅ Streamlined deployment
- ✅ Improved scripts
- ✅ Better documentation

### **Version Updates**
- ✅ Updated to V5.0.0
- ✅ Updated health check endpoints
- ✅ Updated version references

### **Latest Features**
- ✅ **Playbook System**: Complete playbook management with 5 system playbooks
- ✅ **Multi-Product KPI**: Full support for product-level KPI tracking
- ✅ **Enhanced Upload**: Advanced customer profile upload with format detection
- ✅ **Enhanced RAG**: Advanced AI capabilities with conversation history
- ✅ **Performance Summary**: Comprehensive customer performance tracking
- ✅ **Data Quality**: Advanced data management and quality tools

---

## 📁 Key Files

- `docker-compose.v5.yml` - Docker Compose configuration
- `build-and-test-v5.sh` - Local build and test script
- `deploy-v5.sh` - AWS deployment script
- `V5_DEPLOYMENT_GUIDE.md` - Complete deployment guide

---

## 🔧 Configuration

### Environment Variables
Create `docker.env` with:
```bash
FLASK_APP=app_v3_minimal.py
FLASK_ENV=production
OPENAI_API_KEY=your-key-here
```

---

## 📚 Documentation

- **Full Guide:** See `V5_DEPLOYMENT_GUIDE.md`
- **Troubleshooting:** See deployment guide
- **Version History:** See deployment guide

---

## ✅ Ready for Deployment!

V5 is production-ready and includes all necessary improvements for a clean, maintainable deployment.

**Next Steps:**
1. Run `./build-and-test-v5.sh` locally
2. Verify all tests pass
3. Run `./deploy-v5.sh` for AWS deployment

---

**Version:** 5.0.0  
**Status:** Production Ready  
**Last Updated:** December 2024

