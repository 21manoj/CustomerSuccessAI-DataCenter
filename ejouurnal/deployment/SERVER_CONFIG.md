# 🖥️ EC2 Server Configuration

## ✅ **Server Details Confirmed**

```
IP Address:  3.84.178.121
SSH User:    ec2-user
SSH Key:     ~/kpi-dashboard/kpi-dashboard-key.pem
Region:      us-east-1 (N. Virginia)
OS:          Amazon Linux 2 (kernel 4.14)
```

---

## 🔍 **Current Server Status**

### **✅ Already Installed:**
- Docker v25.0.8 ✅
- Nginx (running on ports 80, 443) ✅

### **❌ Not Installed:**
- PM2 (not needed, using Docker)

### **🔌 Ports Currently In Use:**

| Port | Service | Application |
|------|---------|-------------|
| **80** | Nginx | Web server |
| **443** | Nginx | HTTPS |
| **3000** | docker-proxy | KPI Backend |
| **3001** | docker-proxy | ⚠️ CONFLICT! |
| **8080** | docker-proxy | Unknown app |

---

## ⚠️ **PORT CONFLICT RESOLVED**

**Problem:** Port 3001 is already in use!

**Solution:** I've updated Fulfillment app to use:
- **Backend:** Port **3005** (was 3001) ✅
- **Frontend:** Port **3006** (was 3002) ✅

**Updated Files:**
- ✅ `docker-compose.prod.yml` → Port 3005
- ✅ `backend/Dockerfile` → Expose 3005
- ✅ `backend/server.js` → Listen on 3005
- ✅ `nginx/nginx.prod.conf` → Proxy to 3005

---

## 🏗️ **Deployment Plan**

### **Current Setup (KPI App):**
```
Nginx (Port 80/443)
  ↓
KPI Backend (Port 3000)
KPI ? (Port 3001)
? (Port 8080)
```

### **After Fulfillment Deployment:**
```
Nginx (Port 80/443)
  ├── /kpi/* → KPI Backend (Port 3000)
  └── /fulfillment/* → Fulfillment Backend (Port 3005)

Docker Containers:
├── KPI containers (existing)
└── Fulfillment containers (new)
    ├── fulfillment-backend (Port 3005)
    ├── fulfillment-frontend (Port 3006)
    ├── fulfillment-db (PostgreSQL)
    └── fulfillment-nginx (optional)
```

**No conflicts!** ✅

---

## 📋 **Pre-Deployment Checklist**

### **Server Ready:**
- [x] SSH access confirmed
- [x] Docker installed
- [x] Nginx running
- [x] Ports mapped (3005, 3006 available)

### **Deployment Files Ready:**
- [x] Docker configurations updated
- [x] Port conflicts resolved
- [x] Backend API ready
- [x] Database schema ready
- [x] Nginx config ready

### **Still Need:**
- [ ] OpenAI API key (for AI journals) - **What's your preference?**
- [ ] Domain name (optional, for SSL)
- [ ] Confirm KPI app nginx config location

---

## 🎯 **Next Steps (When You're Ready)**

### **1. Quick Check:**
Let me verify KPI app Nginx config:
```bash
ssh -i ~/kpi-dashboard/kpi-dashboard-key.pem ec2-user@3.84.178.121 \
  "sudo cat /etc/nginx/nginx.conf | grep -A 5 location"
```

### **2. Package & Upload:**
```bash
cd /Users/manojgupta/ejouurnal
tar -czf fulfillment-deploy.tar.gz \
  backend/ \
  frontend/ \
  docker-compose.prod.yml \
  nginx/ \
  Makefile \
  deployment/

scp -i ~/kpi-dashboard/kpi-dashboard-key.pem \
  fulfillment-deploy.tar.gz \
  ec2-user@3.84.178.121:/home/ec2-user/
```

### **3. Deploy:**
```bash
ssh -i ~/kpi-dashboard/kpi-dashboard-key.pem ec2-user@3.84.178.121

# Extract
cd /home/ec2-user
tar -xzf fulfillment-deploy.tar.gz

# Copy to /opt
sudo mkdir -p /opt/fulfillment
sudo cp -r * /opt/fulfillment/
cd /opt/fulfillment

# Configure
nano .env  # Add API keys, passwords

# Deploy
sudo docker-compose -f docker-compose.prod.yml up -d
```

---

## 🔐 **Security Notes**

### **What to Configure in `.env`:**

```bash
# Database (REQUIRED)
DB_PASSWORD=choose-a-secure-password-here

# Security (REQUIRED)
JWT_SECRET=random-32-character-string-here

# CORS
CORS_ORIGIN=http://3.84.178.121

# OpenAI (OPTIONAL - for AI journals)
OPENAI_API_KEY=sk-...your-key...

# Or leave empty to use templates
OPENAI_API_KEY=
```

---

## ❓ **Questions for You:**

### **1. OpenAI API Key:**
Do you want to:
- **A)** Provide OpenAI API key (I'll add AI journal generation)
- **B)** Use smart templates instead (zero cost, no AI)
- **C)** Deploy without journals first, add later

### **2. KPI App Details:**
- What's the KPI app URL structure? (`/kpi/*` or something else?)
- Where's the Nginx config? (`/etc/nginx/nginx.conf` or separate?)

### **3. Domain:**
- Do you have a domain for Fulfillment? (e.g., `fulfillment.yourdomain.com`)
- Or use IP for now?

---

## 📊 **Server Capacity Check**

Let me check if server has enough resources:

<function_calls>
<invoke name="run_terminal_cmd">
<parameter name="command">ssh -i ~/kpi-dashboard/kpi-dashboard-key.pem ec2-user@3.84.178.121 "free -h && echo '---' && df -h / && echo '---' && nproc"
