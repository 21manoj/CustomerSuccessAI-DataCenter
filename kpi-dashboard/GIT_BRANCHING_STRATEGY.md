# Git Branching Strategy - MCP Integration

## ✅ Current Status

**Branch Created:** `feature/mcp-integration`  
**Based On:** `main` (latest commit: 2c80ada)  
**Purpose:** Develop MCP external system integration with zero risk to production

---

## 🌳 Branch Structure

```
main (production)
  │
  │ ← V2 with all playbook features (deployed)
  │ ← Commit: 2c80ada "V2 Deployment Complete - Full Playbook System"
  │
  └─── feature/mcp-integration (NEW)
        │
        │ ← All MCP development happens here
        │ ← Safe to experiment, break things, test
        │ ← Never affects production
        │
        └─── (After testing)
              │
              └─→ Merge to main (when ready)
```

---

## 🎯 Development Workflow

### **Phase 1: Development (Week 1-2)**

**On Branch:** `feature/mcp-integration`

```bash
# You're already on this branch!
git branch
# * feature/mcp-integration

# Make changes
# 1. Add FeatureToggle model
# 2. Create mock MCP servers
# 3. Build MCP integration layer
# 4. Add UI toggles

# Commit frequently
git add backend/models.py
git commit -m "Add FeatureToggle model for MCP"

git add backend/mcp_servers/
git commit -m "Add mock Salesforce MCP server"

git add backend/enhanced_rag_with_mcp.py
git commit -m "Add MCP-enhanced RAG with feature toggle"

git add src/components/Settings.tsx
git commit -m "Add MCP toggle in Settings UI"

# Push to GitHub
git push origin feature/mcp-integration
```

### **Phase 2: Testing (Week 3)**

**Still on:** `feature/mcp-integration`

```bash
# Test locally
npm run build
./venv/bin/python backend/run_server.py

# Test all scenarios:
# - MCP enabled
# - MCP disabled
# - Individual systems on/off
# - Error handling

# Fix bugs, commit
git add .
git commit -m "Fix MCP error handling"
git push origin feature/mcp-integration
```

### **Phase 3: Deploy to V2 for Testing (Week 4)**

**Deploy feature branch to V2 (test environment):**

```bash
# On EC2, create V2-test deployment
ssh ec2-user@3.84.178.121

# Clone feature branch
cd /home/ec2-user
git clone -b feature/mcp-integration \
  git@github.com:21manoj/CustomerSuccessAI-Triad.git \
  kpi-dashboard-mcp-test

# Deploy on different ports (9001, 9080)
# Test with real users
# Collect feedback
```

### **Phase 4: Merge to Main (After Success)**

```bash
# Switch to main
git checkout main

# Pull latest
git pull origin main

# Merge feature branch
git merge feature/mcp-integration

# Push to GitHub
git push origin main

# Deploy to production V2
# V1 remains unchanged
```

---

## 🛡️ Safety Benefits

### **Why This Strategy is Perfect:**

✅ **Zero Risk to Production**
- `main` branch stays stable
- V1 and V2 keep running
- No production changes until ready

✅ **Easy Rollback**
- Don't like it? Just don't merge
- Switch back: `git checkout main`
- Delete branch: `git branch -D feature/mcp-integration`

✅ **Isolated Development**
- Experiment freely
- Break things without worry
- Test thoroughly before merge

✅ **Clear History**
- All MCP commits grouped together
- Easy to review changes
- Can cherry-pick commits if needed

✅ **Team Collaboration**
- Others can review on GitHub
- Can create Pull Request
- Get feedback before merge

---

## 📋 Recommended Commits

### **Commit Structure:**

```bash
# 1. Foundation
git commit -m "Add FeatureToggle model and migration"
git commit -m "Add MCP feature toggle API endpoints"

# 2. Mock Servers
git commit -m "Add mock Salesforce MCP server"
git commit -m "Add mock ServiceNow MCP server"
git commit -m "Add mock Survey MCP server"

# 3. Integration
git commit -m "Add MCP integration layer"
git commit -m "Enhance RAG with MCP (feature-toggled)"
git commit -m "Add automatic fallback on MCP errors"

# 4. UI
git commit -m "Add MCP toggle in Settings UI"
git commit -m "Add data source badges in AI Insights"

# 5. Testing
git commit -m "Add MCP integration tests"
git commit -m "Add mock server tests"

# 6. Documentation
git commit -m "Add MCP integration guide"
git commit -m "Update README with MCP features"
```

---

## 🔍 PR Review Checklist

**Before merging to main:**

### **Code Quality:**
- [ ] All tests pass
- [ ] No linter errors
- [ ] Code reviewed
- [ ] Documentation complete

### **Functionality:**
- [ ] Feature toggle works (on/off)
- [ ] Automatic fallback tested
- [ ] All 3 mock servers working
- [ ] UI toggle responsive

### **Safety:**
- [ ] Default is OFF (safe)
- [ ] Rollback tested (instant)
- [ ] Error handling tested
- [ ] Production unaffected

### **Testing:**
- [ ] Tested with MCP ON
- [ ] Tested with MCP OFF
- [ ] Tested individual system toggles
- [ ] Tested error scenarios

---

## 🎯 Deployment Strategy

### **Option 1: Conservative (Recommended)**

```
Week 1-2: Develop on feature/mcp-integration
Week 3: Deploy feature branch to V2-test (port 9001)
Week 4: Test with 1-2 customers
Week 5: Merge to main
Week 6: Deploy to production V2
```

### **Option 2: Aggressive**

```
Week 1: Develop on feature/mcp-integration
Week 2: Test locally + merge to main
Week 3: Deploy to V2 (feature OFF)
Week 4: Enable for test customers
```

---

## 📊 Branch Management Commands

### **Useful Commands:**

```bash
# Check current branch
git branch

# Switch between branches
git checkout main
git checkout feature/mcp-integration

# See changes in feature branch
git diff main feature/mcp-integration

# View commit history
git log --oneline feature/mcp-integration

# Push feature branch to GitHub
git push origin feature/mcp-integration

# Create Pull Request (on GitHub)
# Compare: main ← feature/mcp-integration

# After merge, delete feature branch
git branch -d feature/mcp-integration
git push origin --delete feature/mcp-integration
```

---

## 🎯 Current State

```
✅ Repository: github.com:21manoj/CustomerSuccessAI-Triad
✅ Main branch: Protected, stable, production-ready
✅ Feature branch: feature/mcp-integration (created)
✅ Your current location: feature/mcp-integration

You can now:
1. Develop MCP features safely
2. Test without affecting production
3. Merge when ready (or abandon if not)
```

---

## ✅ Benefits of This Approach

| Benefit | Description |
|---------|-------------|
| **Safety** | Main branch never touched until ready |
| **Flexibility** | Can abandon feature if doesn't work |
| **Testing** | Thorough testing before production |
| **Review** | Team can review on GitHub PR |
| **History** | Clean commit history |
| **Rollback** | Easy to revert if needed |
| **Parallel Work** | Others can work on main |

---

## 💡 Next Steps

**You're now on `feature/mcp-integration` branch!**

Ready to start building:
1. ✅ FeatureToggle model
2. ✅ Mock MCP servers
3. ✅ MCP integration layer
4. ✅ UI toggles

**Want me to start implementing the MCP feature on this branch?** 🚀

---

**Current Git Status:**
- **Branch:** `feature/mcp-integration` ✅
- **Base:** `main` (commit 2c80ada)
- **Status:** Clean, ready for development
- **Safe to:** Make any changes without affecting production
