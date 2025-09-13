#!/bin/bash

# AWS EC2 Deployment Script for KPI Dashboard
set -e

# Configuration
AWS_REGION="us-east-1"
INSTANCE_TYPE="t3.micro"  # Free tier eligible
AMI_ID="ami-0023921b4fcd5382b"  # Amazon Linux 2 AMI (latest)
KEY_NAME="kpi-dashboard-key"
SECURITY_GROUP_NAME="kpi-dashboard-sg"
INSTANCE_NAME="kpi-dashboard"

echo "🚀 Starting EC2 deployment for KPI Dashboard..."
echo "AWS Region: $AWS_REGION"
echo "Instance Type: $INSTANCE_TYPE (Free Tier Eligible)"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists aws; then
    echo "❌ AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Step 1: Create Security Group
echo "🔒 Creating security group..."

# Check if security group already exists
if aws ec2 describe-security-groups --group-names $SECURITY_GROUP_NAME --region $AWS_REGION >/dev/null 2>&1; then
    echo "Security group $SECURITY_GROUP_NAME already exists"
else
    # Create security group
    aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Security group for KPI Dashboard" \
        --region $AWS_REGION
    
    echo "✅ Security group created"
fi

# Get security group ID
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
    --group-names $SECURITY_GROUP_NAME \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $AWS_REGION)

echo "Security Group ID: $SECURITY_GROUP_ID"

# Add security group rules
echo "🔧 Configuring security group rules..."

# Allow HTTP
aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "HTTP rule already exists"

# Allow HTTPS
aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "HTTPS rule already exists"

# Allow SSH (replace with your IP)
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 22 \
    --cidr $MY_IP/32 \
    --region $AWS_REGION 2>/dev/null || echo "SSH rule already exists"

# Allow backend port
aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 5059 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || echo "Backend port rule already exists"

echo "✅ Security group rules configured"

# Step 2: Create Key Pair
echo "🔑 Creating key pair..."

if aws ec2 describe-key-pairs --key-names $KEY_NAME --region $AWS_REGION >/dev/null 2>&1; then
    echo "Key pair $KEY_NAME already exists"
else
    # Create key pair
    aws ec2 create-key-pair \
        --key-name $KEY_NAME \
        --query 'KeyMaterial' \
        --output text \
        --region $AWS_REGION > $KEY_NAME.pem
    
    # Set proper permissions
    chmod 400 $KEY_NAME.pem
    
    echo "✅ Key pair created: $KEY_NAME.pem"
fi

# Step 3: Launch EC2 Instance
echo "🖥️ Launching EC2 instance..."

# Check if instance already exists
EXISTING_INSTANCE=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=running,pending" \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --output text \
    --region $AWS_REGION)

if [ -n "$EXISTING_INSTANCE" ]; then
    echo "Instance $INSTANCE_NAME already exists: $EXISTING_INSTANCE"
    INSTANCE_ID=$EXISTING_INSTANCE
else
    # Launch new instance
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id $AMI_ID \
        --count 1 \
        --instance-type $INSTANCE_TYPE \
        --key-name $KEY_NAME \
        --security-group-ids $SECURITY_GROUP_ID \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
        --query 'Instances[0].InstanceId' \
        --output text \
        --region $AWS_REGION)
    
    echo "✅ Instance launched: $INSTANCE_ID"
fi

# Step 4: Wait for instance to be running
echo "⏳ Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $AWS_REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region $AWS_REGION)

echo "✅ Instance is running!"
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"

# Step 5: Create deployment script for EC2
echo "📝 Creating deployment script for EC2..."

cat > ec2-setup.sh << 'EOF'
#!/bin/bash

# EC2 Setup Script
set -e

echo "🚀 Setting up KPI Dashboard on EC2..."

# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo yum install -y git

# Clone repository
git clone https://github.com/21manoj/CustomerSuccessAI-Triad.git
cd CustomerSuccessAI-Triad

# Create environment file
cat > .env << 'ENVEOF'
FLASK_ENV=production
SQLALCHEMY_DATABASE_URI=sqlite:///instance/kpi_dashboard.db
OPENAI_API_KEY=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
ENVEOF

# Start application
docker-compose up -d

echo "✅ KPI Dashboard deployed successfully!"
echo "Access your application at: http://$(curl -s https://checkip.amazonaws.com)"
EOF

# Step 6: Copy setup script to EC2
echo "📤 Copying setup script to EC2..."

# Wait a bit more for SSH to be ready
sleep 30

# Copy setup script
scp -i $KEY_NAME.pem -o StrictHostKeyChecking=no ec2-setup.sh ec2-user@$PUBLIC_IP:/home/ec2-user/

# Step 7: Run setup script on EC2
echo "🔧 Running setup script on EC2..."

ssh -i $KEY_NAME.pem -o StrictHostKeyChecking=no ec2-user@$PUBLIC_IP 'chmod +x ec2-setup.sh && ./ec2-setup.sh'

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📋 Summary:"
echo "   Instance ID: $INSTANCE_ID"
echo "   Public IP: $PUBLIC_IP"
echo "   Application URL: http://$PUBLIC_IP"
echo "   SSH Command: ssh -i $KEY_NAME.pem ec2-user@$PUBLIC_IP"
echo ""
echo "💰 Cost: FREE (using t2.micro free tier)"
echo ""
echo "🔧 To check status:"
echo "   docker-compose ps"
echo "   docker-compose logs -f"
echo ""
echo "🛑 To stop:"
echo "   docker-compose down"
echo ""
echo "🗑️ To terminate instance:"
echo "   aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $AWS_REGION"
