# Deploy V2 to AWS - Manual Steps

## Overview
Deploy V2 alongside V1 on the same EC2 instance without disturbing V1.

**V1:** Port 5059 (existing)  
**V2:** Port 5060 (new)  

---

## Instance Information

**Instance ID:** i-05d943311f6c90fdf  
**Region:** us-east-1  
**Public IP:** 3.84.178.121  
**Current:** V1 running on port 5059  

---

## Deployment Steps

### Step 1: Upload V2 Package to EC2

```bash
# From your local machine
cd /Users/manojgupta/kpi-dashboard

# Upload the V2 package
scp -i ~/.ssh/your-key.pem \
  kpi-dashboard-v2-production.tar.gz \
  ec2-user@3.84.178.121:/home/ec2-user/

# Verify upload
ssh -i ~/.ssh/your-key.pem ec2-user@3.84.178.121 "ls -lh /home/ec2-user/kpi-dashboard-v2-production.tar.gz"
```

### Step 2: SSH to EC2 and Extract

```bash
# SSH to instance
ssh -i ~/.ssh/your-key.pem ec2-user@3.84.178.121

# Once connected:
cd /home/ec2-user
mkdir -p kpi-dashboard-v2
cd kpi-dashboard-v2
tar -xzf ../kpi-dashboard-v2-production.tar.gz

# Verify extraction
ls -la
```

### Step 3: Set Up Python Environment

```bash
# Still in SSH session
cd /home/ec2-user/kpi-dashboard-v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# Create instance directory
mkdir -p instance
```

### Step 4: Run Database Migrations

```bash
# Still in venv
cd backend

# Run migrations
python migrations/add_playbook_executions_table.py
python migrations/add_playbook_reports_table.py

# Go back to root
cd ..
```

### Step 5: Create V2 Server Script

```bash
# Create run_server_v2.py
cat > backend/run_server_v2.py << 'EOF'
#!/usr/bin/env python3
"""V2 Server runner on port 5060"""
from app import app

if __name__ == '__main__':
    print("Starting KPI Dashboard V2 on port 5060...")
    app.run(host='0.0.0.0', port=5060, debug=False)
EOF

chmod +x backend/run_server_v2.py
```

### Step 6: Create Systemd Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/kpi-dashboard-v2.service > /dev/null <<'EOF'
[Unit]
Description=KPI Dashboard V2
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/kpi-dashboard-v2
Environment="PATH=/home/ec2-user/kpi-dashboard-v2/venv/bin"
ExecStart=/home/ec2-user/kpi-dashboard-v2/venv/bin/python backend/run_server_v2.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/kpi-dashboard-v2.log
StandardError=append:/var/log/kpi-dashboard-v2-error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable and start V2
sudo systemctl enable kpi-dashboard-v2
sudo systemctl start kpi-dashboard-v2

# Check status
sudo systemctl status kpi-dashboard-v2
```

### Step 7: Update Security Group

```bash
# Exit SSH, run from local machine
aws ec2 authorize-security-group-ingress \
  --group-id sg-YOUR-SECURITY-GROUP-ID \
  --protocol tcp \
  --port 5060 \
  --cidr 0.0.0.0/0 \
  --region us-east-1

# Or find security group automatically:
SG_ID=$(aws ec2 describe-instances \
  --instance-ids i-05d943311f6c90fdf \
  --region us-east-1 \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5060 \
  --cidr 0.0.0.0/0 \
  --region us-east-1
```

### Step 8: Create Sample Customers

```bash
# SSH back to instance
ssh -i ~/.ssh/your-key.pem ec2-user@3.84.178.121

cd /home/ec2-user/kpi-dashboard-v2
source venv/bin/activate

# Create ACME customer
python backend/create_acme_customer.py

# Verify
python -c "from backend.app import app, db; from backend.models import Customer; 
app.app_context().push(); 
print(f'Customers: {Customer.query.count()}')"
```

### Step 9: Configure Nginx (Optional - for domain)

```bash
# Create Nginx config for V2
sudo tee /etc/nginx/conf.d/kpi-dashboard-v2.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name v2.customersuccessai.triadpartners.ai;

    location / {
        proxy_pass http://localhost:5060;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Reload Nginx
sudo nginx -t && sudo systemctl reload nginx
```

### Step 10: Verify Deployment

```bash
# Test from local machine
curl http://3.84.178.121:5060/

# Test login
curl -X POST http://3.84.178.121:5060/api/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "test@test.com", "password": "test123"}'

# Test accounts
curl http://3.84.178.121:5060/api/accounts -H 'X-Customer-ID: 1'
```

---

## Verification Checklist

- [ ] V2 package uploaded to EC2
- [ ] V2 extracted to /home/ec2-user/kpi-dashboard-v2
- [ ] Python dependencies installed
- [ ] Database migrations completed
- [ ] Systemd service created and started
- [ ] Port 5060 open in security group
- [ ] V2 health endpoint responds
- [ ] V2 login works
- [ ] V2 can fetch accounts
- [ ] V1 still working on port 5059

---

## Service Management

### Check V2 Status
```bash
sudo systemctl status kpi-dashboard-v2
```

### View V2 Logs
```bash
sudo tail -f /var/log/kpi-dashboard-v2.log
sudo tail -f /var/log/kpi-dashboard-v2-error.log
```

### Restart V2
```bash
sudo systemctl restart kpi-dashboard-v2
```

### Stop V2
```bash
sudo systemctl stop kpi-dashboard-v2
```

---

## Access URLs

### V1 (Existing - Unchanged)
- **URL:** http://3.84.178.121:5059
- **Domain:** https://customersuccessai.triadpartners.ai (if configured)
- **Status:** Running, not disturbed

### V2 (New Deployment)
- **URL:** http://3.84.178.121:5060
- **Domain:** https://v2.customersuccessai.triadpartners.ai (if configured)
- **Status:** Ready to deploy

---

## Directory Structure on EC2

```
/home/ec2-user/
├── kpi-dashboard/          (V1 - existing, port 5059)
│   ├── backend/
│   ├── build/
│   ├── instance/
│   └── venv/
│
└── kpi-dashboard-v2/       (V2 - new, port 5060)
    ├── backend/
    ├── build/
    ├── instance/
    ├── migrations/
    ├── docs/
    └── venv/
```

---

## Rollback Plan

If V2 has issues:

```bash
# Stop V2 service
sudo systemctl stop kpi-dashboard-v2

# V1 continues running unaffected
```

To remove V2 completely:

```bash
sudo systemctl stop kpi-dashboard-v2
sudo systemctl disable kpi-dashboard-v2
sudo rm /etc/systemd/system/kpi-dashboard-v2.service
sudo systemctl daemon-reload
rm -rf /home/ec2-user/kpi-dashboard-v2
```

---

## DNS Configuration (Optional)

If you want a separate domain for V2:

### Route 53 Records

**V1 (existing):**
```
customersuccessai.triadpartners.ai → 3.84.178.121:5059
```

**V2 (new):**
```
v2.customersuccessai.triadpartners.ai → 3.84.178.121:5060
```

### Or Create A/B Testing

Use AWS Application Load Balancer:
- 50% traffic → V1 (port 5059)
- 50% traffic → V2 (port 5060)

---

## Next Steps

1. **Review this guide**
2. **Prepare your SSH key** (~/.ssh/your-key.pem)
3. **Run deployment** (follow steps above)
4. **Test V2** (http://3.84.178.121:5060)
5. **Keep V1** running (http://3.84.178.121:5059)

---

**Ready to deploy V2 alongside V1!** 🚀

**Both versions will run simultaneously for testing and comparison.**

