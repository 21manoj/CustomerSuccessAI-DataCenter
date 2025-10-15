# V2 Deployment Instructions - AWS EC2

## Status: READY TO DEPLOY (Manual Process Required)

**Reason:** AWS permissions needed:
- S3 bucket creation (s3:CreateBucket)
- SSM command execution (ssm:SendCommand)  
- EC2 security group modification (ec2:AuthorizeSecurityGroupIngress)

**Solution:** Manual deployment or request AWS permissions

---

## Quick Deployment (Manual Steps)

### Prerequisites
- SSH access to EC2 instance (i-05d943311f6c90fdf)
- EC2 instance IP: 3.84.178.121
- SSH key pair for ec2-user

---

## Deployment Steps

### Step 1: Upload V2 Package

From your local machine:

```bash
cd /Users/manojgupta/kpi-dashboard

# Option A: If you have SSH key
scp -i ~/.ssh/your-key.pem \
  kpi-dashboard-v2-production.tar.gz \
  ec2-user@3.84.178.121:/home/ec2-user/

# Option B: Use SCP with password (if configured)
scp kpi-dashboard-v2-production.tar.gz \
  ec2-user@3.84.178.121:/home/ec2-user/

# Option C: Upload to a public URL and download on EC2
# (Upload to Dropbox/Google Drive, get link, then wget on EC2)
```

### Step 2: SSH to EC2

```bash
# If you have SSH key
ssh -i ~/.ssh/your-key.pem ec2-user@3.84.178.121

# Or if password auth is enabled
ssh ec2-user@3.84.178.121
```

### Step 3: Extract and Setup (Run on EC2)

```bash
# Create V2 directory
mkdir -p /home/ec2-user/kpi-dashboard-v2
cd /home/ec2-user/kpi-dashboard-v2

# Extract package
tar -xzf ../kpi-dashboard-v2-production.tar.gz

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# Create instance directory for database
mkdir -p instance

echo "✅ V2 setup complete"
```

### Step 4: Run Database Migrations

```bash
# Still in V2 directory with venv activated
cd backend

python migrations/add_playbook_executions_table.py
python migrations/add_playbook_reports_table.py

cd ..

echo "✅ Migrations complete"
```

### Step 5: Create ACME Customer Data

```bash
# Create second customer for multi-tenant demo
python backend/create_acme_customer.py

echo "✅ ACME customer created"
```

### Step 6: Create V2 Server Script

```bash
# Create server script for port 5060
cat > backend/run_server_v2.py << 'EOF'
#!/usr/bin/env python3
"""V2 Server runner on port 5060"""
import sys
import os

# Ensure we're in the backend directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("Starting KPI Dashboard V2")
    print("Port: 5060")
    print("Version: 2.0.0")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5060, debug=False)
EOF

chmod +x backend/run_server_v2.py

echo "✅ V2 server script created"
```

### Step 7: Create Systemd Service

```bash
# Create systemd service for V2
sudo tee /etc/systemd/system/kpi-dashboard-v2.service > /dev/null <<'EOF'
[Unit]
Description=KPI Dashboard V2 Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/kpi-dashboard-v2
Environment="PATH=/home/ec2-user/kpi-dashboard-v2/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/home/ec2-user/kpi-dashboard-v2/backend"
ExecStart=/home/ec2-user/kpi-dashboard-v2/venv/bin/python /home/ec2-user/kpi-dashboard-v2/backend/run_server_v2.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/kpi-dashboard-v2.log
StandardError=append:/var/log/kpi-dashboard-v2-error.log

[Install]
WantedBy=multi-user.target
EOF

# Create log files
sudo touch /var/log/kpi-dashboard-v2.log
sudo touch /var/log/kpi-dashboard-v2-error.log
sudo chown ec2-user:ec2-user /var/log/kpi-dashboard-v2*.log

# Reload systemd
sudo systemctl daemon-reload

# Enable V2 service
sudo systemctl enable kpi-dashboard-v2

# Start V2 service
sudo systemctl start kpi-dashboard-v2

# Check status
echo ""
echo "V2 Service Status:"
sudo systemctl status kpi-dashboard-v2 --no-pager -l

echo "✅ V2 service started"
```

### Step 8: Verify V2 is Running

```bash
# Check if V2 is listening on port 5060
netstat -tuln | grep 5060

# Test V2 health endpoint
curl http://localhost:5060/

# Test V2 login
curl -X POST http://localhost:5060/api/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "test@test.com", "password": "test123"}'

echo "✅ V2 verification complete"
```

### Step 9: Update Security Group (From Local Machine)

```bash
# Exit SSH, run from your local machine

# Get security group ID
SG_ID=$(aws ec2 describe-instances \
  --instance-ids i-05d943311f6c90fdf \
  --region us-east-1 \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

echo "Security Group: $SG_ID"

# Add rule for port 5060
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5060 \
  --cidr 0.0.0.0/0 \
  --region us-east-1

echo "✅ Port 5060 opened in security group"
```

### Step 10: Test from Internet

```bash
# From your local machine
curl http://3.84.178.121:5060/

# Test login
curl -X POST http://3.84.178.121:5060/api/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "acme@acme.com", "password": "acme123"}'

# Access in browser
open http://3.84.178.121:5060
```

---

## Alternative: Deploy with AWS Console

If SSH is not available, use AWS Systems Manager Session Manager:

1. Go to AWS Console → EC2 → Instances
2. Select instance i-05d943311f6c90fdf
3. Click "Connect" → "Session Manager"
4. Run the commands from Step 3-8 above

---

## Verification Checklist

After deployment:

- [ ] V2 service running: `sudo systemctl status kpi-dashboard-v2`
- [ ] Port 5060 listening: `netstat -tuln | grep 5060`
- [ ] Health endpoint responds: `curl http://localhost:5060/`
- [ ] Login works: Test with test@test.com and acme@acme.com
- [ ] Accounts API works: `curl http://localhost:5060/api/accounts -H 'X-Customer-ID: 1'`
- [ ] V1 still running: `curl http://localhost:5059/`
- [ ] Port 5060 open externally: `curl http://3.84.178.121:5060/`
- [ ] Browser access works: http://3.84.178.121:5060

---

## Service URLs

### V1 (Existing - Unchanged)
- **Internal:** http://localhost:5059
- **External:** http://3.84.178.121:5059
- **Domain:** https://customersuccessai.triadpartners.ai
- **Status:** Running, not touched

### V2 (New Deployment)
- **Internal:** http://localhost:5060
- **External:** http://3.84.178.121:5060
- **Domain:** Setup needed (see below)
- **Status:** Ready to deploy

---

## DNS Setup for V2 (Optional)

If you want a separate domain for V2:

### Option 1: Subdomain
```
v2.customersuccessai.triadpartners.ai → 3.84.178.121:5060
```

### Option 2: Path-based routing
```
customersuccessai.triadpartners.ai/v2 → port 5060
customersuccessai.triadpartners.ai → port 5059
```

Would require Nginx configuration update.

---

## Troubleshooting

### Issue: Can't SSH to EC2

**Solution 1:** Use AWS Systems Manager Session Manager
- No SSH key needed
- Access via AWS Console

**Solution 2:** Request SSH key from AWS admin
- Download .pem file
- Place in ~/.ssh/
- chmod 400 ~/.ssh/your-key.pem

### Issue: Port 5060 not accessible

**Solution:** Update security group
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-XXX \
  --protocol tcp \
  --port 5060 \
  --cidr 0.0.0.0/0 \
  --region us-east-1
```

### Issue: V2 service won't start

**Check logs:**
```bash
sudo journalctl -u kpi-dashboard-v2 -n 50
sudo tail -f /var/log/kpi-dashboard-v2-error.log
```

---

## Rollback

If V2 has issues:

```bash
# Stop V2
sudo systemctl stop kpi-dashboard-v2

# V1 continues running normally
# No changes made to V1
```

---

## Summary

**Package Ready:** ✅ kpi-dashboard-v2-production.tar.gz (2.5 MB)  
**Deployment Method:** Manual SSH or AWS Console Session Manager  
**Target:** EC2 instance i-05d943311f6c90fdf  
**Port:** 5060 (V2) alongside 5059 (V1)  
**Impact on V1:** NONE - V1 continues running  

**Required Permissions:**
- SSH access to EC2 instance, OR
- AWS Systems Manager Session Manager access, OR
- Request someone with permissions to run the deployment

**Estimated Time:** 15-20 minutes

---

**Next Steps:**

1. ✅ V2 package created and ready
2. ⏳ Need SSH access or AWS Console access to EC2
3. ⏳ Follow steps 1-10 above
4. ✅ V2 will run on port 5060
5. ✅ V1 continues on port 5059

**V2 is ready - just need EC2 access to complete deployment!** 🚀

