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
