# 🧪 Local Testing Guide

## 🚀 **Docker Containers Starting...**

Building and starting 4 containers:
1. **fulfillment-backend** - Node.js API (Port 3005)
2. **fulfillment-frontend** - React app (Port 3006)
3. **fulfillment-postgres** - PostgreSQL database
4. **fulfillment-nginx** - Reverse proxy (Port 8080)

---

## ⏳ **Build Process (First Time)**

Expect ~5-10 minutes for initial build:
1. Downloading base images (node:20-alpine, postgres:16, nginx)
2. Installing dependencies (npm install)
3. Building frontend (npm run build)
4. Creating containers

**Subsequent starts:** ~30 seconds

---

## 📊 **What's Running on Your Mac**

### **KPI Dashboard (Already Running):**
- `kpi-dashboard-frontend` → Port 80
- `kpi-dashboard-backend` → Port 5059

### **Fulfillment App (Starting Now):**
- `fulfillment-backend` → Port 3005
- `fulfillment-frontend` → Port 3006
- `fulfillment-postgres` → Internal (5432)
- `fulfillment-nginx` → Port 8080

**No port conflicts!** ✅

---

## 🧪 **How to Test After Startup**

### **1. Check Container Status:**
```bash
docker ps --filter "name=fulfillment"
```

### **2. View Logs:**
```bash
# All logs
docker-compose logs -f

# Specific container
docker logs -f fulfillment-backend
```

### **3. Test Backend Health:**
```bash
curl http://localhost:3005/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-17T...",
  "uptime": 12.345,
  "database": "connected"
}
```

### **4. Test AI Journal Generation:**
```bash
# Create test user
curl -X POST http://localhost:3005/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test_local_001",
    "name": "Test User",
    "email": "test@test.com"
  }'

# Create check-in
curl -X POST http://localhost:3005/api/check-ins \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test_local_001",
    "dayPart": "morning",
    "mood": 4,
    "arousal": "medium",
    "contexts": ["Work"],
    "microAct": "Meditation"
  }'

# Generate AI journal (THIS WILL USE OPENAI!)
curl -X POST http://localhost:3005/api/journals/generate \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test_local_001",
    "tone": "reflective"
  }'
```

**This will call OpenAI API and generate a real journal!** ✨

### **5. Test Frontend:**
```bash
open http://localhost:3006
```

---

## 📊 **Monitor Progress**

### **Watch Build Progress:**
```bash
docker-compose logs -f backend
```

### **Check All Containers:**
```bash
docker ps -a
```

### **View Resource Usage:**
```bash
docker stats
```

---

## 🔍 **Troubleshooting**

### **If Build Fails:**
```bash
# View error logs
docker-compose logs backend

# Rebuild from scratch
docker-compose down -v
docker-compose up -d --build
```

### **If Database Won't Connect:**
```bash
# Check postgres logs
docker logs fulfillment-postgres

# Wait for database to initialize (first time takes ~30 seconds)
docker-compose logs -f postgres
```

### **If Port Already in Use:**
```bash
# Check what's using the port
lsof -i :3005

# Stop conflicting container
docker stop <container-name>
```

---

## ✅ **Success Indicators**

When ready, you'll see:
```bash
docker ps --filter "name=fulfillment"

# Should show:
fulfillment-backend     Up X minutes (healthy)   3005/tcp
fulfillment-frontend    Up X minutes (healthy)   3006/tcp
fulfillment-postgres    Up X minutes (healthy)   5432/tcp
fulfillment-nginx       Up X minutes             8080/tcp
```

---

## 🧪 **Test Checklist**

After containers are up:
- [ ] Backend health: `curl http://localhost:3005/health`
- [ ] Database connected (check backend logs)
- [ ] Frontend accessible: `http://localhost:3006`
- [ ] Create test user (curl command above)
- [ ] Generate AI journal (curl command above) ✨
- [ ] Verify journal contains AI-generated text
- [ ] Test regeneration with different tone
- [ ] Check OpenAI usage in dashboard

---

## 💰 **Cost Monitoring**

While testing:
- Each journal generation = ~$0.002
- Testing with 5-10 journals = ~$0.01-0.02
- Check OpenAI dashboard: https://platform.openai.com/usage

---

## 🎯 **Next Steps After Testing**

Once local testing is successful:
1. ✅ Verify AI journal generation works
2. ✅ Test all 4 tones
3. ✅ Test personal notes integration
4. ✅ Check all API endpoints
5. ✅ Review logs for errors

Then:
- Package for EC2 deployment
- Upload to 3.84.178.121
- Deploy to production

---

**Containers are building now...** 

**Check progress:**
```bash
docker-compose logs -f
```

**This will take ~5 minutes for first build.** ⏰

