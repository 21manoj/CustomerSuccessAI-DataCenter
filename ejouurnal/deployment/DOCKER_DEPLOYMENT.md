# 🐳 Docker Deployment Guide
## Fulfillment App - Containerized Deployment

---

## 🎯 **Why Docker?**

✅ **Isolation** - Runs alongside KPI app without conflicts  
✅ **Portability** - Same container works everywhere  
✅ **Easy Updates** - Just rebuild and restart  
✅ **Resource Control** - Set CPU/memory limits  
✅ **Scalability** - Easy to scale horizontally  

---

## 🚀 **Quick Start (5 Minutes)**

### **1. On Local Machine:**
```bash
cd /Users/manojgupta/ejouurnal
tar -czf fulfillment-docker.tar.gz backend/ frontend/ docker-compose.prod.yml .env.example nginx/ deployment/
```

### **2. Upload to EC2:**
```bash
scp fulfillment-docker.tar.gz ubuntu@YOUR_EC2_IP:/home/ubuntu/
```

### **3. On EC2 Server:**
```bash
# Extract files
cd /home/ubuntu
tar -xzf fulfillment-docker.tar.gz

# Run Docker setup script
chmod +x deployment/docker-deploy.sh
sudo deployment/docker-deploy.sh

# Copy files to /opt/fulfillment
sudo cp -r * /opt/fulfillment/

# Update environment variables
cd /opt/fulfillment
sudo nano .env  # Update passwords!

# Start application
sudo docker-compose -f docker-compose.prod.yml up -d
```

---

## 📦 **What Gets Deployed**

### **Docker Containers:**
```
┌─────────────────────────────────────────────┐
│           Docker Host (EC2)                 │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  nginx-prod (Port 80/443)            │  │
│  │  Reverse Proxy + SSL                 │  │
│  └───────┬──────────────────┬───────────┘  │
│          │                  │               │
│          ▼                  ▼               │
│  ┌──────────────┐  ┌──────────────┐        │
│  │  backend-prod│  │frontend-prod │        │
│  │  Port: 3001  │  │  Port: 3002  │        │
│  └──────┬───────┘  └──────────────┘        │
│         │                                   │
│         ▼                                   │
│  ┌──────────────┐                          │
│  │  postgres    │                          │
│  │  Port: 5432  │                          │
│  └──────────────┘                          │
│                                             │
└─────────────────────────────────────────────┘
```

### **Containers:**
1. **fulfillment-nginx-prod** - Nginx reverse proxy
2. **fulfillment-backend-prod** - Node.js API
3. **fulfillment-frontend-prod** - React app (nginx)
4. **fulfillment-db-prod** - PostgreSQL database

### **Volumes:**
- `postgres_data` - Database persistence
- `nginx_logs` - Nginx logs
- `/opt/fulfillment/backups` - Database backups

---

## 🛠️ **Docker Commands**

### **Container Management:**
```bash
# View all containers
docker ps -a --filter "name=fulfillment"

# View logs
docker logs -f fulfillment-backend-prod
docker logs -f fulfillment-frontend-prod
docker logs -f fulfillment-nginx-prod

# Restart container
docker restart fulfillment-backend-prod

# Stop all containers
docker-compose -f docker-compose.prod.yml down

# Start all containers
docker-compose -f docker-compose.prod.yml up -d

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build
```

### **Database Management:**
```bash
# Connect to database
docker exec -it fulfillment-db-prod psql -U fulfillment_user -d fulfillment

# Backup database
sudo /opt/fulfillment/backup.sh

# Restore database
docker exec -i fulfillment-db-prod psql -U fulfillment_user -d fulfillment < backup.sql

# View database logs
docker logs fulfillment-db-prod
```

### **Resource Monitoring:**
```bash
# View resource usage
docker stats

# View container details
docker inspect fulfillment-backend-prod

# View networks
docker network ls

# View volumes
docker volume ls
```

---

## 🔄 **Deployment Workflow**

### **Initial Deployment:**
```bash
cd /opt/fulfillment
sudo docker-compose -f docker-compose.prod.yml up -d
```

### **Update Application:**
```bash
# Method 1: Using deploy script
sudo /opt/fulfillment/deploy.sh

# Method 2: Manual
cd /opt/fulfillment
sudo docker-compose -f docker-compose.prod.yml pull
sudo docker-compose -f docker-compose.prod.yml up -d --build
```

### **Rollback:**
```bash
# Use previous image
docker-compose -f docker-compose.prod.yml down
docker run -d fulfillment-backend:previous-tag
```

---

## 🔐 **Environment Variables**

Edit `/opt/fulfillment/.env`:

```bash
# Database (REQUIRED - Change these!)
DB_PASSWORD=your-secure-db-password-here

# Security (REQUIRED - Change these!)
JWT_SECRET=minimum-32-character-random-string-here

# CORS (Update with your domain)
CORS_ORIGIN=https://fulfillment.yourdomain.com

# Optional: AWS S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET=

# Optional: OpenAI
OPENAI_API_KEY=

# Optional: SendGrid
SENDGRID_API_KEY=
```

**After updating `.env`:**
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🌐 **Nginx Configuration**

### **Update Domain:**
Edit `/opt/fulfillment/nginx/nginx.prod.conf`:

```nginx
server_name fulfillment.yourdomain.com;  # Change this
```

### **Setup SSL (Let's Encrypt):**
```bash
# Stop nginx container
docker stop fulfillment-nginx-prod

# Get certificate
sudo docker run -it --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -p 80:80 \
  certbot/certbot certonly --standalone \
  -d fulfillment.yourdomain.com

# Restart nginx
docker start fulfillment-nginx-prod
```

### **Auto-renew SSL:**
Add to crontab:
```bash
0 3 * * * docker run --rm -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot renew && docker restart fulfillment-nginx-prod
```

---

## 📊 **Health Checks**

### **Built-in Health Checks:**
```bash
# Backend health
curl http://localhost:3001/health

# Frontend health
curl http://localhost:3002/health

# Check Docker health status
docker ps --filter "name=fulfillment" --format "table {{.Names}}\t{{.Status}}"
```

### **Automated Monitoring:**
Docker automatically restarts unhealthy containers.

---

## 💾 **Backup & Restore**

### **Automated Backups:**
```bash
# Setup daily backup (add to crontab)
sudo crontab -e

# Add this line:
0 2 * * * /opt/fulfillment/backup.sh
```

### **Manual Backup:**
```bash
sudo /opt/fulfillment/backup.sh
```

### **Restore from Backup:**
```bash
# Stop backend
docker stop fulfillment-backend-prod

# Restore
gunzip < /opt/fulfillment/backups/fulfillment_20240316_020000.sql.gz | \
  docker exec -i fulfillment-db-prod psql -U fulfillment_user -d fulfillment

# Start backend
docker start fulfillment-backend-prod
```

---

## 🔧 **Development vs Production**

### **Development (Local):**
```bash
# Uses docker-compose.yml
docker-compose up

# Access:
# - Backend: http://localhost:3001
# - Frontend: http://localhost:3002
# - Database: localhost:5433
```

### **Production (EC2):**
```bash
# Uses docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d

# Access:
# - Via Nginx: http://your-domain/fulfillment
# - API: http://your-domain/api/fulfillment
```

---

## 🚨 **Troubleshooting**

### **Container won't start:**
```bash
# Check logs
docker logs fulfillment-backend-prod

# Check environment variables
docker exec fulfillment-backend-prod env

# Inspect container
docker inspect fulfillment-backend-prod
```

### **Database connection issues:**
```bash
# Check if database is running
docker ps | grep postgres

# Test connection
docker exec fulfillment-backend-prod nc -zv postgres 5432

# Check database logs
docker logs fulfillment-db-prod
```

### **Nginx 502 Bad Gateway:**
```bash
# Check if backend is running
docker ps | grep backend

# Check backend health
curl http://localhost:3001/health

# Check nginx logs
docker logs fulfillment-nginx-prod
```

### **Port conflicts:**
```bash
# Check what's using the port
sudo netstat -tulpn | grep 3001

# Stop conflicting service
docker stop <container-name>
```

---

## 📈 **Performance Optimization**

### **Resource Limits:**
Add to `docker-compose.prod.yml`:

```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 512M
      reservations:
        cpus: '0.5'
        memory: 256M
```

### **Database Tuning:**
```bash
# Edit postgresql.conf
docker exec -it fulfillment-db-prod bash
vi /var/lib/postgresql/data/pgdata/postgresql.conf

# Increase shared_buffers, work_mem, etc.
```

### **Scaling:**
```bash
# Scale backend to 3 instances
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

---

## 🔒 **Security Checklist**

- [ ] Change default passwords in `.env`
- [ ] Update JWT_SECRET with random string
- [ ] Configure SSL/HTTPS
- [ ] Enable firewall (UFW)
- [ ] Use Docker secrets for sensitive data
- [ ] Keep Docker images updated
- [ ] Scan images for vulnerabilities: `docker scan fulfillment-backend`
- [ ] Use non-root users in containers (already configured)
- [ ] Limit container resources
- [ ] Enable Docker logging
- [ ] Regular security updates

---

## 📊 **Monitoring**

### **Container Stats:**
```bash
docker stats
```

### **Logs:**
```bash
# Tail all logs
docker-compose -f docker-compose.prod.yml logs -f

# Specific container
docker logs -f --tail 100 fulfillment-backend-prod
```

### **Disk Usage:**
```bash
docker system df
docker volume ls
```

### **Cleanup:**
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Complete cleanup
docker system prune -a --volumes
```

---

## 🎉 **Advantages over Traditional Deployment**

| Aspect | Docker | Traditional (PM2) |
|--------|--------|-------------------|
| **Isolation** | ✅ Complete | ⚠️ Shared dependencies |
| **Updates** | ✅ Zero-downtime | ⚠️ Requires restart |
| **Rollback** | ✅ Instant | ⚠️ Manual |
| **Scaling** | ✅ Easy | ⚠️ Complex |
| **Resource Control** | ✅ Built-in | ⚠️ System-level |
| **Portability** | ✅ Any server | ⚠️ Environment-specific |

---

## 📞 **Support**

**Check Status:**
```bash
sudo /opt/fulfillment/status.sh
```

**View Logs:**
```bash
docker logs -f fulfillment-backend-prod
```

**Health Check:**
```bash
curl http://localhost:3001/health
```

---

**Deployment Complete!** 🐳

Your Fulfillment app is now running in Docker containers on AWS EC2!

