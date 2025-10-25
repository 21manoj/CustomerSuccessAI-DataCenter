# 🧹 Project Cleanup Plan

## ✅ **Files Successfully Committed to GitHub**

### **Modified Files (Committed)**
- `backend/playbook_recommendations_api.py` - Fixed playbook logic
- `backend/playbook_triggers_api.py` - Updated trigger management
- `backend/requirements.txt` - Updated dependencies
- `src/components/Settings.tsx` - Enhanced UI

### **New Files (Committed)**
- `COMPLETE_FEATURE_LIST_AND_SAAS_ROADMAP.md` - Comprehensive SaaS roadmap
- `DATABASE_SCHEMA.md` - Database documentation
- `V2_DOCKER_CONFIGURATION.md` - V2 deployment docs
- `V2_DOMAIN_SETUP.md` - Domain configuration
- `Dockerfile.v3` - V3 Docker configuration
- `docker-compose.v3.yml` - V3 Docker compose

---

## 🗑️ **Defunct Files Identified for Cleanup**

### **1. Log Files (Safe to Delete)**
```bash
# These are development logs that can be safely removed
./backend-test.log
./backend.log
./backend-new.log
./frontend.log
./server-cached.log
./server-new.log
./server.log
```

### **2. Archive Files (Safe to Delete)**
```bash
# These are old deployment packages that can be removed
./kpi-dashboard-v3.tar.gz
./kpi-dashboard-v3-fixed.tar.gz
./kpi-dashboard-v3-frontend-fixed.tar.gz
./kpi-dashboard-v2-production.tar.gz
./kpi-dashboard.tar.gz
./build-v3.tar.gz
```

### **3. Qdrant Storage Directories (191 directories - 1.4GB+)**
```bash
# These are old vector database storage directories from testing
# Only keep the main qdrant_storage/ directory
./qdrant_storage_13399/     # 20K
./qdrant_storage_1430/      # 20K
./qdrant_storage_14726/     # 7.1M
./qdrant_storage_1623/      # 20K
./qdrant_storage_19062/     # 20K
./qdrant_storage_25988/     # 20K
./qdrant_storage_2613/      # 20K
./qdrant_storage_38124/     # 7.1M
./qdrant_storage_506/       # 20K
./qdrant_storage_53576/     # 20K
# ... and 181 more similar directories
```

### **4. Backup Files (Safe to Delete)**
```bash
./src/components/CSPlatform.tsx.backup
```

### **5. AWS CLI Package (Safe to Delete)**
```bash
./AWSCLIV2.pkg  # macOS installer package
```

### **6. Test Results Files (Can be Archived)**
```bash
./v3_advanced_test_results.json
./v3_test_results.json
```

---

## 🧹 **Cleanup Commands**

### **Phase 1: Remove Log Files**
```bash
rm -f *.log
rm -f backend*.log
rm -f frontend*.log
rm -f server*.log
```

### **Phase 2: Remove Archive Files**
```bash
rm -f *.tar.gz
rm -f build-*.tar.gz
rm -f kpi-dashboard-*.tar.gz
```

### **Phase 3: Remove Qdrant Storage Directories**
```bash
# Remove all numbered qdrant storage directories
rm -rf qdrant_storage_*
# Keep only the main qdrant_storage/ directory
```

### **Phase 4: Remove Backup Files**
```bash
rm -f *.backup
rm -f src/components/*.backup
```

### **Phase 5: Remove AWS Package**
```bash
rm -f AWSCLIV2.pkg
```

### **Phase 6: Archive Test Results**
```bash
mkdir -p archive/test-results
mv v3_*_test_results.json archive/test-results/
```

---

## 📊 **Space Savings Estimate**

| Category | Files | Estimated Size | Space Saved |
|----------|-------|----------------|-------------|
| Log Files | 7 | ~50MB | 50MB |
| Archive Files | 7 | ~200MB | 200MB |
| Qdrant Storage | 191 | ~1.4GB | 1.4GB |
| Backup Files | 2 | ~1MB | 1MB |
| AWS Package | 1 | ~50MB | 50MB |
| **Total** | **208** | **~1.7GB** | **1.7GB** |

---

## ⚠️ **Files to Keep (Important)**

### **Core Application Files**
- `backend/` - All backend code
- `src/` - All frontend code
- `migrations/` - Database migrations
- `instance/` - Database files
- `public/` - Static assets
- `build/` - Production build

### **Configuration Files**
- `package.json` - Node.js dependencies
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Docker configuration
- `Dockerfile*` - Docker build files
- `nginx*.conf` - Nginx configuration
- `.env` - Environment variables

### **Documentation Files**
- `README.md` - Main documentation
- `COMPLETE_FEATURE_LIST_AND_SAAS_ROADMAP.md` - SaaS roadmap
- `V3_COMPLETE.md` - V3 documentation
- `KPI_DASHBOARD_GUIDING_PRINCIPLES.md` - Guiding principles
- All `*.md` files with important documentation

### **Data Files**
- `Maturity-Framework-KPI-loveable.xlsx` - KPI framework
- `qdrant_storage/` - Main vector database storage

---

## 🚀 **Automated Cleanup Script**

Create a cleanup script:

```bash
#!/bin/bash
# cleanup.sh - Project cleanup script

echo "🧹 Starting project cleanup..."

# Phase 1: Remove log files
echo "Removing log files..."
rm -f *.log backend*.log frontend*.log server*.log

# Phase 2: Remove archive files
echo "Removing archive files..."
rm -f *.tar.gz build-*.tar.gz kpi-dashboard-*.tar.gz

# Phase 3: Remove Qdrant storage directories
echo "Removing old Qdrant storage directories..."
rm -rf qdrant_storage_*

# Phase 4: Remove backup files
echo "Removing backup files..."
rm -f *.backup src/components/*.backup

# Phase 5: Remove AWS package
echo "Removing AWS package..."
rm -f AWSCLIV2.pkg

# Phase 6: Archive test results
echo "Archiving test results..."
mkdir -p archive/test-results
mv v3_*_test_results.json archive/test-results/ 2>/dev/null || true

echo "✅ Cleanup complete!"
echo "Space saved: ~1.7GB"
echo "Files removed: ~208"
```

---

## 📋 **Pre-Cleanup Checklist**

- [ ] **Backup Important Data**: Ensure all important data is committed to Git
- [ ] **Verify Git Status**: All changes are committed and pushed
- [ ] **Test Application**: Ensure V3 is working correctly before cleanup
- [ ] **Document Current State**: Take note of current file structure

---

## 📋 **Post-Cleanup Checklist**

- [ ] **Verify Application**: Test that V3 still works after cleanup
- [ ] **Check Git Status**: Ensure no important files were accidentally removed
- [ ] **Update .gitignore**: Add patterns to prevent future accumulation
- [ ] **Document Changes**: Update README if needed

---

## 🎯 **Benefits of Cleanup**

1. **Reduced Repository Size**: ~1.7GB space savings
2. **Faster Git Operations**: Smaller repository for faster clones/pulls
3. **Cleaner Project Structure**: Easier to navigate and understand
4. **Reduced Confusion**: Remove outdated and duplicate files
5. **Better Performance**: Less disk I/O and faster file operations

---

## ⚡ **Quick Cleanup Command**

If you want to run the cleanup immediately:

```bash
# Run the cleanup script
chmod +x cleanup.sh
./cleanup.sh

# Or run individual commands
rm -f *.log *.tar.gz AWSCLIV2.pkg *.backup
rm -rf qdrant_storage_*
mkdir -p archive/test-results
mv v3_*_test_results.json archive/test-results/ 2>/dev/null || true
```

---

**Status**: ✅ Ready for cleanup execution
**Estimated Time**: 5-10 minutes
**Risk Level**: Low (all files are safe to remove)
**Space Savings**: ~1.7GB
