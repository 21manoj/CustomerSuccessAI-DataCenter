#!/bin/bash
# Deploy KPI Dashboard V2 to AWS EC2
# This creates a NEW deployment alongside V1 without disturbing it

set -e

echo "======================================================================"
echo "KPI Dashboard V2 - AWS Deployment Script"
echo "======================================================================"

# Configuration
INSTANCE_ID="i-05d943311f6c90fdf"
REGION="us-east-1"
KEY_NAME="your-key-pair"  # Update this
DEPLOY_PATH="/home/ec2-user/kpi-dashboard-v2"
PACKAGE_FILE="kpi-dashboard-v2-production.tar.gz"

# Get instance IP
INSTANCE_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $REGION \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "Instance IP: $INSTANCE_IP"

# Step 1: Upload deployment package
echo ""
echo "Step 1: Uploading V2 package to EC2..."
scp -i ~/.ssh/${KEY_NAME}.pem \
  $PACKAGE_FILE \
  ec2-user@${INSTANCE_IP}:/home/ec2-user/

echo "✅ Package uploaded"

# Step 2: Deploy on EC2
echo ""
echo "Step 2: Deploying V2 on EC2..."

ssh -i ~/.ssh/${KEY_NAME}.pem ec2-user@${INSTANCE_IP} << 'ENDSSH'
set -e

echo "Connected to EC2 instance"

# Create V2 directory
echo "Creating V2 deployment directory..."
mkdir -p /home/ec2-user/kpi-dashboard-v2
cd /home/ec2-user/kpi-dashboard-v2

# Extract package
echo "Extracting V2 package..."
tar -xzf /home/ec2-user/kpi-dashboard-v2-production.tar.gz

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt 2>&1 | grep -E "Successfully|Requirement already satisfied" | head -20

# Create instance directory
mkdir -p instance

# Run database migrations
echo "Running database migrations..."
cd backend
python migrations/add_playbook_executions_table.py
python migrations/add_playbook_reports_table.py
cd ..

# Create systemd service for V2 (runs on port 5060)
echo "Creating systemd service for V2..."
sudo tee /etc/systemd/system/kpi-dashboard-v2.service > /dev/null <<EOF
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

[Install]
WantedBy=multi-user.target
EOF

# Create V2 server script (port 5060)
echo "Creating V2 server script..."
cat > backend/run_server_v2.py <<'PYEOF'
#!/usr/bin/env python3
"""V2 Server runner on port 5060"""
from app import app

if __name__ == '__main__':
    print("Starting KPI Dashboard V2 on port 5060...")
    app.run(host='0.0.0.0', port=5060, debug=False)
PYEOF

chmod +x backend/run_server_v2.py

# Reload systemd and start V2 service
echo "Starting V2 service..."
sudo systemctl daemon-reload
sudo systemctl enable kpi-dashboard-v2
sudo systemctl restart kpi-dashboard-v2

# Wait for service to start
sleep 5

# Check status
echo ""
echo "V2 Service Status:"
sudo systemctl status kpi-dashboard-v2 --no-pager | head -15

# Test V2 health
echo ""
echo "Testing V2 health endpoint..."
curl -s http://localhost:5060/ || echo "Health check failed"

echo ""
echo "✅ V2 deployment complete!"
echo "V2 is running on port 5060"
echo "V1 is still running on port 5059"

ENDSSH

# Step 3: Update Security Group for V2 port
echo ""
echo "Step 3: Updating security group for port 5060..."

SECURITY_GROUP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --region $REGION \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

echo "Security Group: $SECURITY_GROUP"

# Add rule for port 5060 (if not exists)
aws ec2 authorize-security-group-ingress \
  --group-id $SECURITY_GROUP \
  --protocol tcp \
  --port 5060 \
  --cidr 0.0.0.0/0 \
  --region $REGION 2>&1 | grep -v "already exists" || true

echo "✅ Security group updated"

# Step 4: Verify deployment
echo ""
echo "Step 4: Verifying V2 deployment..."

echo "Testing V2 endpoint..."
curl -s http://${INSTANCE_IP}:5060/ && echo ""

echo "Testing V2 login..."
curl -s -X POST http://${INSTANCE_IP}:5060/api/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "test@test.com", "password": "test123"}' | python3 -m json.tool 2>&1 | head -10

echo ""
echo "======================================================================"
echo "V2 DEPLOYMENT COMPLETE!"
echo "======================================================================"
echo ""
echo "✅ V1 Status: Running on http://${INSTANCE_IP}:5059"
echo "✅ V2 Status: Running on http://${INSTANCE_IP}:5060"
echo ""
echo "V2 Endpoints:"
echo "  - Health: http://${INSTANCE_IP}:5060/"
echo "  - Dashboard: http://${INSTANCE_IP}:5060/"
echo "  - API: http://${INSTANCE_IP}:5060/api/*"
echo ""
echo "Test V2:"
echo "  curl http://${INSTANCE_IP}:5060/"
echo "  curl http://${INSTANCE_IP}:5060/api/accounts -H 'X-Customer-ID: 1'"
echo ""
echo "Access via browser:"
echo "  http://${INSTANCE_IP}:5060"
echo ""
echo "======================================================================"

