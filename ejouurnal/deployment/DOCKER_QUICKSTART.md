# 🐳 Docker Quick Start

## ⚡ **Deploy in 3 Commands**

### **On EC2 Server:**

```bash
# 1. Install Docker
sudo deployment/docker-deploy.sh

# 2. Update passwords
nano .env

# 3. Start everything
docker-compose -f docker-compose.prod.yml up -d
```

**Done!** Your app is running. 🎉

---

## 🧪 **Test Locally First**

### **On Your Mac:**

```bash
cd /Users/manojgupta/ejouurnal

# Start development environment
docker-compose up -d

# Wait 10 seconds for startup
sleep 10

# Test
curl http://localhost:3001/health
open http://localhost:3002
```

---

## 📦 **What You Get**

### **4 Docker Containers:**
1. **fulfillment-backend** - Node.js API (Port 3001)
2. **fulfillment-frontend** - React app (Port 3002)
3. **fulfillment-db** - PostgreSQL database
4. **fulfillment-nginx** - Reverse proxy (Port 80/443)

### **Everything Runs Together:**
- All containers in same network
- Database persists in volume
- Logs automatically rotated
- Auto-restart on crash
- Health checks built-in

---

## 🔄 **Common Commands**

### **With Makefile (Easier):**
```bash
make help        # Show all commands
make dev         # Start development
make prod        # Start production
make logs        # View logs
make status      # Check status
make db-backup   # Backup database
make deploy      # Deploy new version
```

### **With Docker Compose:**
```bash
# Start
docker-compose -f docker-compose.prod.yml up -d

# Stop
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart
docker-compose -f docker-compose.prod.yml restart
```

---

## 🚀 **EC2 Deployment Steps**

### **1. Prepare Package:**
```bash
cd /Users/manojgupta/ejouurnal
tar -czf fulfillment-docker.tar.gz \
  backend/ \
  frontend/ \
  nginx/ \
  docker-compose.prod.yml \
  .env.example \
  Makefile \
  deployment/
```

### **2. Upload to EC2:**
```bash
scp fulfillment-docker.tar.gz ubuntu@YOUR_EC2_IP:/home/ubuntu/
```

### **3. Deploy:**
```bash
ssh ubuntu@YOUR_EC2_IP

# Extract
cd /home/ubuntu
tar -xzf fulfillment-docker.tar.gz

# Setup Docker
sudo deployment/docker-deploy.sh

# Copy to /opt
sudo mkdir -p /opt/fulfillment
sudo cp -r * /opt/fulfillment/
cd /opt/fulfillment

# Configure
cp .env.example .env
sudo nano .env  # Update passwords!

# Start
sudo docker-compose -f docker-compose.prod.yml up -d

# Check
sudo make status
```

---

## 🎯 **URLs After Deployment**

**If using domain:**
- Frontend: `https://fulfillment.yourdomain.com/fulfillment/`
- API: `https://fulfillment.yourdomain.com/api/fulfillment/`

**If using IP:**
- Frontend: `http://YOUR_EC2_IP:3002/`
- API: `http://YOUR_EC2_IP:3001/`

---

## 💡 **Pro Tips**

### **Run alongside KPI App:**
Both apps can run on same EC2:
- **KPI App:** Ports 3000 (backend), 3003 (frontend)
- **Fulfillment:** Ports 3001 (backend), 3002 (frontend)

No conflicts! Each in its own Docker network.

### **Share Nginx:**
You can use one Nginx for both apps:
```nginx
# In nginx config:
location /kpi/ { proxy_pass http://kpi-frontend; }
location /fulfillment/ { proxy_pass http://fulfillment-frontend; }
```

### **Monitor Resources:**
```bash
docker stats  # Real-time CPU/memory
```

---

## 🆘 **Troubleshooting**

**Container won't start?**
```bash
docker logs fulfillment-backend-prod
```

**Port already in use?**
```bash
# Change ports in docker-compose.prod.yml:
ports:
  - "3005:3001"  # Use 3005 instead of 3001
```

**Database won't connect?**
```bash
docker exec -it fulfillment-db-prod psql -U fulfillment_user -d fulfillment
```

---

## ✅ **Success Checklist**

After deployment:
- [ ] All 4 containers running: `docker ps`
- [ ] Backend healthy: `curl http://localhost:3001/health`
- [ ] Frontend accessible: `curl http://localhost:3002`
- [ ] Database connected: `docker exec fulfillment-db-prod psql -U fulfillment_user -d fulfillment -c "SELECT 1"`
- [ ] Logs clean: `docker logs fulfillment-backend-prod`

---

**Docker deployment is MUCH easier than traditional deployment!** 🐳

**Questions?** Check `DOCKER_DEPLOYMENT.md` for complete guide.

