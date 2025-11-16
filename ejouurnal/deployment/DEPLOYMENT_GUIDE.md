# 🚀 AWS EC2 Deployment Guide
## Fulfillment App - Running alongside KPI Application

---

## 📋 **Prerequisites**

- EC2 instance running (with KPI app already deployed)
- SSH access to EC2 server
- Domain name (optional, for HTTPS)
- AWS account access

---

## 🎯 **Quick Start**

### **Step 1: Copy Files to Server**

From your local machine:

```bash
# Create deployment package
cd /Users/manojgupta/ejouurnal
tar -czf fulfillment-app.tar.gz backend/ frontend/ deployment/

# Upload to EC2
scp fulfillment-app.tar.gz ubuntu@your-ec2-ip:/home/ubuntu/

# SSH into server
ssh ubuntu@your-ec2-ip

# Extract files
cd /home/ubuntu
tar -xzf fulfillment-app.tar.gz
```

### **Step 2: Run Setup Script**

```bash
# Make script executable
chmod +x deployment/aws-setup.sh

# Run setup (requires sudo)
sudo ./deployment/aws-setup.sh
```

**This script will:**
- ✅ Install Node.js, PM2, Nginx, PostgreSQL
- ✅ Create application directory (`/var/www/fulfillment`)
- ✅ Setup database and user
- ✅ Configure Nginx (separate from KPI app)
- ✅ Create PM2 ecosystem file
- ✅ Setup firewall rules
- ✅ Create helper scripts

### **Step 3: Deploy Application Code**

```bash
# Copy backend files
sudo cp -r backend/* /var/www/fulfillment/backend/

# Copy frontend files
sudo cp -r frontend/* /var/www/fulfillment/frontend/

# Install backend dependencies
cd /var/www/fulfillment/backend
sudo npm install --production

# Run database migrations
sudo npm run migrate

# Build frontend
cd /var/www/fulfillment/frontend
sudo npm install
sudo npm run build
```

### **Step 4: Start Services**

```bash
# Start PM2 processes
cd /var/www/fulfillment
sudo pm2 start ecosystem.config.js

# Save PM2 configuration
sudo pm2 save

# Setup PM2 to start on boot
sudo pm2 startup
# (Run the command PM2 outputs)

# Check status
sudo pm2 status
```

### **Step 5: Configure DNS & SSL** (Optional but Recommended)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d fulfillment.yourdomain.com

# Certbot will automatically:
# - Configure Nginx for HTTPS
# - Setup auto-renewal
```

---

## 🌐 **Architecture**

Your EC2 server will now run:

```
┌─────────────────────────────────────────────┐
│           EC2 Instance (Ubuntu)             │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │           Nginx (Port 80/443)        │  │
│  │  ┌────────────┐   ┌────────────┐    │  │
│  │  │ KPI App    │   │ Fulfillment│    │  │
│  │  │ /kpi/*     │   │ /fulfillment/*│  │  │
│  │  └────────────┘   └────────────┘    │  │
│  └──────────────────────────────────────┘  │
│           │                     │           │
│           ▼                     ▼           │
│  ┌────────────┐       ┌────────────┐       │
│  │  KPI API   │       │Fulfillment │       │
│  │ Port: 3000 │       │  Backend   │       │
│  │            │       │ Port: 3001 │       │
│  └────────────┘       └────────────┘       │
│                              │              │
│                              ▼              │
│                     ┌────────────┐          │
│                     │ PostgreSQL │          │
│                     │ fulfillment│          │
│                     │    DB      │          │
│                     └────────────┘          │
└─────────────────────────────────────────────┘
```

---

## 📂 **File Structure on Server**

```
/var/www/fulfillment/
├── backend/
│   ├── server.js           # Main API server
│   ├── package.json        # Dependencies
│   ├── migrations/         # Database migrations
│   └── .env                # Environment config
├── frontend/
│   ├── build/              # Production build
│   └── package.json
├── logs/
│   ├── backend-error.log
│   ├── backend-out.log
│   ├── frontend-error.log
│   └── frontend-out.log
├── uploads/                # User uploads (if any)
├── backups/                # Database backups
├── ecosystem.config.js     # PM2 configuration
├── deploy.sh               # Quick deployment script
├── backup.sh               # Database backup script
└── status.sh               # Status check script
```

---

## 🔧 **Configuration**

### **Backend Environment Variables**

Edit `/var/www/fulfillment/backend/.env`:

```bash
NODE_ENV=production
PORT=3001

DB_HOST=localhost
DB_PORT=5432
DB_NAME=fulfillment
DB_USER=fulfillment_user
DB_PASSWORD=your-secure-password-here

JWT_SECRET=your-super-secret-jwt-key
CORS_ORIGIN=https://fulfillment.yourdomain.com
```

### **Nginx Configuration**

Located at: `/etc/nginx/sites-available/fulfillment`

Key routes:
- `/api/fulfillment/*` → Backend API (Port 3001)
- `/fulfillment/*` → Frontend app
- `/fulfillment/health` → Health check

### **PM2 Process Management**

Configuration: `/var/www/fulfillment/ecosystem.config.js`

Processes:
1. **fulfillment-backend** - API server (2 instances, cluster mode)
2. **fulfillment-frontend** - Static file server (1 instance)

---

## 🛠️ **Common Commands**

### **PM2 Process Management:**
```bash
# View all processes
pm2 list

# View logs
pm2 logs fulfillment-backend
pm2 logs fulfillment-frontend

# Restart services
pm2 restart fulfillment-backend
pm2 restart fulfillment-frontend

# Monitor in real-time
pm2 monit

# Stop services
pm2 stop fulfillment-backend
pm2 stop fulfillment-frontend
```

### **Nginx:**
```bash
# Test configuration
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Restart
sudo systemctl restart nginx

# View logs
sudo tail -f /var/log/nginx/fulfillment_access.log
sudo tail -f /var/log/nginx/fulfillment_error.log
```

### **Database:**
```bash
# Connect to database
sudo -u postgres psql fulfillment

# Backup database
sudo /var/www/fulfillment/backup.sh

# Restore from backup
sudo -u postgres psql fulfillment < backup.sql
```

### **Application Scripts:**
```bash
# Deploy new version
sudo /var/www/fulfillment/deploy.sh

# Check application status
sudo /var/www/fulfillment/status.sh

# Backup database
sudo /var/www/fulfillment/backup.sh
```

---

## 🚀 **Deployment Workflow**

### **Deploying Updates:**

```bash
# On local machine:
cd /Users/manojgupta/ejouurnal
npm run build  # Build frontend
tar -czf update.tar.gz backend/ frontend/
scp update.tar.gz ubuntu@your-ec2-ip:/home/ubuntu/

# On EC2 server:
cd /home/ubuntu
tar -xzf update.tar.gz

# Run deployment script
cd /var/www/fulfillment
sudo ./deploy.sh
```

### **Using Git (Recommended):**

```bash
# On EC2 server:
cd /var/www/fulfillment
sudo git pull origin main
sudo ./deploy.sh
```

---

## 📊 **Monitoring & Logs**

### **Health Checks:**
```bash
# Backend API
curl http://localhost:3001/health

# Frontend
curl http://localhost:3002

# Via Nginx
curl http://your-domain/fulfillment/health
```

### **View Logs:**
```bash
# Application logs (PM2)
pm2 logs fulfillment-backend --lines 100
pm2 logs fulfillment-frontend --lines 100

# Nginx logs
sudo tail -f /var/log/nginx/fulfillment_access.log
sudo tail -f /var/log/nginx/fulfillment_error.log

# System logs
sudo journalctl -u fulfillment-backend
```

---

## 🔒 **Security Checklist**

- [ ] Change default database password
- [ ] Update JWT_SECRET in .env
- [ ] Enable HTTPS with Let's Encrypt
- [ ] Configure firewall (UFW)
- [ ] Enable fail2ban for SSH protection
- [ ] Set up automated backups
- [ ] Configure monitoring (optional: CloudWatch, Datadog)
- [ ] Enable rate limiting (already configured in Express)
- [ ] Regular security updates: `sudo apt-get update && sudo apt-get upgrade`

---

## 🆘 **Troubleshooting**

### **Backend not starting:**
```bash
# Check logs
pm2 logs fulfillment-backend

# Check database connection
sudo -u postgres psql fulfillment

# Verify environment variables
cat /var/www/fulfillment/backend/.env

# Check port availability
sudo netstat -tulpn | grep 3001
```

### **Nginx 502 Bad Gateway:**
```bash
# Check if backend is running
pm2 list

# Check backend logs
pm2 logs fulfillment-backend

# Restart backend
pm2 restart fulfillment-backend

# Check Nginx error logs
sudo tail -f /var/log/nginx/fulfillment_error.log
```

### **Database connection issues:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Restart PostgreSQL
sudo systemctl restart postgresql

# Check database exists
sudo -u postgres psql -l | grep fulfillment

# Test connection
sudo -u postgres psql fulfillment -c "SELECT NOW();"
```

### **Permission issues:**
```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/fulfillment

# Fix permissions
sudo chmod -R 755 /var/www/fulfillment
sudo chmod -R 775 /var/www/fulfillment/logs
sudo chmod -R 775 /var/www/fulfillment/uploads
```

---

## 🔄 **Backup & Recovery**

### **Automated Backups:**

Add to crontab:
```bash
# Edit crontab
sudo crontab -e

# Add daily backup at 2 AM
0 2 * * * /var/www/fulfillment/backup.sh

# Add weekly cleanup
0 3 * * 0 find /var/www/fulfillment/backups -mtime +30 -delete
```

### **Manual Backup:**
```bash
sudo /var/www/fulfillment/backup.sh
```

### **Restore from Backup:**
```bash
# Stop backend
pm2 stop fulfillment-backend

# Restore database
sudo -u postgres psql fulfillment < /var/www/fulfillment/backups/backup_file.sql

# Start backend
pm2 start fulfillment-backend
```

---

## 📈 **Performance Optimization**

### **PM2 Clustering:**
Already configured in `ecosystem.config.js` - backend runs 2 instances

### **Nginx Caching:**
Already configured - static assets cached for 30 days

### **Database Optimization:**
```sql
-- Create indexes (already in schema)
-- Monitor slow queries
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;

-- Analyze tables
ANALYZE users;
ANALYZE check_ins;
```

### **Monitor Resources:**
```bash
# CPU and Memory
htop

# Disk usage
df -h

# PM2 monitoring
pm2 monit
```

---

## 🎉 **Success Checklist**

After deployment, verify:

- [ ] Backend API responding: `curl http://localhost:3001/health`
- [ ] Frontend accessible: `http://your-domain/fulfillment`
- [ ] Database connected and tables created
- [ ] PM2 processes running: `pm2 list`
- [ ] Nginx serving both KPI and Fulfillment apps
- [ ] SSL certificate installed (if using HTTPS)
- [ ] Logs being written correctly
- [ ] Backups scheduled

---

## 📞 **Support**

If you encounter issues:
1. Check application logs: `pm2 logs`
2. Check Nginx logs: `/var/log/nginx/`
3. Run status check: `/var/www/fulfillment/status.sh`
4. Check database: `sudo -u postgres psql fulfillment`

---

**Deployment Complete!** 🚀

Your Fulfillment app is now running on AWS EC2 alongside your KPI application!

