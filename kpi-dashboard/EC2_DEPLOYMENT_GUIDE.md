# AWS EC2 Deployment Guide for KPI Dashboard

## 🚀 **EC2 Free Tier Benefits**
- **750 hours/month** of t2.micro instances (1 year free)
- **30 GB** of EBS storage
- **2 million I/O operations** with EBS
- **1 GB** of snapshot storage
- **15 GB** of bandwidth out per month

## 📋 **Required AWS Permissions**

Your AWS user needs these permissions. Ask your AWS administrator to attach these policies:

### **EC2 Permissions:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:*",
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "ec2:DescribeInstances",
                "ec2:DescribeImages",
                "ec2:DescribeKeyPairs",
                "ec2:DescribeSecurityGroups",
                "ec2:CreateSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:CreateKeyPair",
                "ec2:ImportKeyPair"
            ],
            "Resource": "*"
        }
    ]
}
```

### **IAM Permissions (for EC2 roles):**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole",
                "iam:GetRole",
                "iam:ListRoles",
                "iam:CreateRole",
                "iam:AttachRolePolicy"
            ],
            "Resource": "*"
        }
    ]
}
```

## 🛠️ **Step-by-Step EC2 Deployment**

### **Step 1: Create Security Group**
```bash
# Create security group for web traffic
aws ec2 create-security-group \
    --group-name kpi-dashboard-sg \
    --description "Security group for KPI Dashboard" \
    --region us-east-1

# Allow HTTP traffic
aws ec2 authorize-security-group-ingress \
    --group-name kpi-dashboard-sg \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region us-east-1

# Allow HTTPS traffic
aws ec2 authorize-security-group-ingress \
    --group-name kpi-dashboard-sg \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region us-east-1

# Allow SSH access (replace with your IP)
aws ec2 authorize-security-group-ingress \
    --group-name kpi-dashboard-sg \
    --protocol tcp \
    --port 22 \
    --cidr YOUR_IP/32 \
    --region us-east-1

# Allow backend port
aws ec2 authorize-security-group-ingress \
    --group-name kpi-dashboard-sg \
    --protocol tcp \
    --port 5059 \
    --cidr 0.0.0.0/0 \
    --region us-east-1
```

### **Step 2: Create Key Pair**
```bash
# Create key pair for SSH access
aws ec2 create-key-pair \
    --key-name kpi-dashboard-key \
    --query 'KeyMaterial' \
    --output text > kpi-dashboard-key.pem

# Set proper permissions
chmod 400 kpi-dashboard-key.pem
```

### **Step 3: Launch EC2 Instance**
```bash
# Launch t2.micro instance (free tier eligible)
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --count 1 \
    --instance-type t2.micro \
    --key-name kpi-dashboard-key \
    --security-groups kpi-dashboard-sg \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=kpi-dashboard}]' \
    --region us-east-1
```

### **Step 4: Get Instance Details**
```bash
# Get instance ID and public IP
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=kpi-dashboard" \
    --query 'Reservations[*].Instances[*].[InstanceId,PublicIpAddress,State.Name]' \
    --output table \
    --region us-east-1
```

## 🐳 **Docker Deployment on EC2**

### **Step 5: Connect to EC2 Instance**
```bash
# SSH into your instance
ssh -i kpi-dashboard-key.pem ec2-user@YOUR_PUBLIC_IP
```

### **Step 6: Install Docker on EC2**
```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add ec2-user to docker group
sudo usermod -a -G docker ec2-user

# Log out and back in, or run:
newgrp docker
```

### **Step 7: Install Docker Compose**
```bash
# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### **Step 8: Deploy Application**
```bash
# Clone your repository (or upload files)
git clone https://github.com/21manoj/CustomerSuccessAI-Triad.git
cd CustomerSuccessAI-Triad

# Create environment file
cat > .env << EOF
FLASK_ENV=production
SQLALCHEMY_DATABASE_URI=sqlite:///instance/kpi_dashboard.db
OPENAI_API_KEY=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
EOF

# Deploy with Docker Compose
docker-compose up -d
```

## 🌐 **Alternative: Manual Setup (No Docker)**

### **Step 9: Install Python and Node.js**
```bash
# Install Python 3.11
sudo yum install -y python3 python3-pip

# Install Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Install nginx
sudo yum install -y nginx
```

### **Step 10: Setup Backend**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export FLASK_ENV=production
export OPENAI_API_KEY="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"

# Run backend
cd backend
python app.py &
```

### **Step 11: Setup Frontend**
```bash
# Install dependencies
npm install

# Build for production
npm run build

# Setup nginx
sudo cp nginx.conf /etc/nginx/nginx.conf
sudo systemctl start nginx
sudo systemctl enable nginx
```

## 🔧 **Nginx Configuration**

Create `/etc/nginx/nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server localhost:5059;
    }

    server {
        listen 80;
        server_name _;

        # Frontend
        location / {
            root /home/ec2-user/CustomerSuccessAI-Triad/build;
            index index.html;
            try_files $uri $uri/ /index.html;
        }

        # Backend API
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## 💰 **Cost Estimation**

| Resource | Free Tier | Monthly Cost |
|----------|-----------|--------------|
| t2.micro (750 hrs) | ✅ Free | $0 |
| EBS Storage (30GB) | ✅ Free | $0 |
| Data Transfer (15GB) | ✅ Free | $0 |
| **Total** | | **$0** |

## 🚀 **Quick Start Script**

I'll create a deployment script that automates the entire process once you have permissions.

## 📞 **Next Steps**

1. **Request EC2 permissions** from your AWS administrator
2. **Run the deployment commands** above
3. **Access your app** at `http://YOUR_EC2_PUBLIC_IP`

## 🔍 **Troubleshooting**

### **Common Issues:**
1. **Permission denied**: Ensure your user has EC2 permissions
2. **Port not accessible**: Check security group rules
3. **Docker not starting**: Ensure Docker service is running
4. **App not loading**: Check nginx configuration and backend logs

### **Useful Commands:**
```bash
# Check instance status
aws ec2 describe-instances --instance-ids i-1234567890abcdef0

# Check security groups
aws ec2 describe-security-groups --group-names kpi-dashboard-sg

# View logs
docker-compose logs -f
sudo journalctl -u nginx -f
```
