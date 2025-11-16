# ⚡ Quick Deployment Steps

## 🚀 **Deploy in 5 Minutes**

### **1. Prepare Files** (on your local machine)
```bash
cd /Users/manojgupta/ejouurnal
tar -czf fulfillment.tar.gz backend/ frontend/ deployment/
```

### **2. Upload to EC2**
```bash
scp fulfillment.tar.gz ubuntu@YOUR_EC2_IP:/home/ubuntu/
```

### **3. SSH into EC2**
```bash
ssh ubuntu@YOUR_EC2_IP
```

### **4. Extract and Setup**
```bash
cd /home/ubuntu
tar -xzf fulfillment.tar.gz
chmod +x deployment/aws-setup.sh
sudo deployment/aws-setup.sh
```

### **5. Deploy Code**
```bash
sudo cp -r backend/* /var/www/fulfillment/backend/
sudo cp -r frontend/* /var/www/fulfillment/frontend/

cd /var/www/fulfillment/backend
sudo npm install --production
sudo psql -U fulfillment_user -d fulfillment -f migrations/001_initial_schema.sql

cd /var/www/fulfillment/frontend
sudo npm install
sudo npm run build
```

### **6. Start**
```bash
cd /var/www/fulfillment
sudo pm2 start ecosystem.config.js
sudo pm2 save
sudo pm2 startup
```

### **7. Test**
```bash
curl http://localhost:3001/health
curl http://localhost:3002
```

## ✅ **Done!**

Access your app:
- **Backend API:** `http://YOUR_EC2_IP/api/fulfillment/`
- **Frontend:** `http://YOUR_EC2_IP/fulfillment/`

---

## 🔧 **Important Configuration**

Update these files before deploying:

1. `/var/www/fulfillment/backend/.env`
   - Change `DB_PASSWORD`
   - Change `JWT_SECRET`
   - Set `CORS_ORIGIN` to your domain

2. `/etc/nginx/sites-available/fulfillment`
   - Update `server_name` with your domain

3. Restart services after changes:
```bash
pm2 restart all
sudo systemctl reload nginx
```

---

## 📊 **Ports Used**

- **KPI App Backend:** 3000 (existing)
- **Fulfillment Backend:** 3001
- **Fulfillment Frontend:** 3002
- **Nginx:** 80, 443

---

## 🆘 **Quick Fixes**

**Backend not working?**
```bash
pm2 logs fulfillment-backend
pm2 restart fulfillment-backend
```

**Database issues?**
```bash
sudo -u postgres psql fulfillment
```

**Nginx 502?**
```bash
pm2 list  # Check if backend is running
sudo systemctl status nginx
```

