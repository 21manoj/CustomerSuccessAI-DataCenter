# AWS Lightsail Deployment Guide

## Step 1: Create Lightsail Instance

1. Go to [AWS Lightsail Console](https://console.aws.amazon.com/lightsail/)
2. Click **"Create instance"**
3. **Platform**: Linux/Unix
4. **Blueprint**: Docker
5. **Instance plan**: 
   - **$5/month**: 512 MB RAM, 1 vCPU (for testing)
   - **$10/month**: 1 GB RAM, 1 vCPU (recommended for production)
6. **Instance name**: `kpi-dashboard`
7. **Availability zone**: Any
8. Click **"Create instance"**

## Step 2: Connect to Your Instance

1. Wait for instance to be **"Running"** (2-3 minutes)
2. Click on your instance name
3. Click **"Connect using SSH"** (browser-based SSH)
4. Or download the SSH key and use terminal

## Step 3: Deploy Your Application

### Option A: Deploy from ECR (Recommended)
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 822824391150.dkr.ecr.us-east-1.amazonaws.com

# Pull and run backend
docker run -d --name kpi-backend \
  -p 5059:5059 \
  -e FLASK_ENV=production \
  -e SQLALCHEMY_DATABASE_URI=sqlite:///instance/kpi_dashboard.db \
  -e OPENAI_API_KEY=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 \
  822824391150.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-backend:latest

# Pull and run frontend
docker run -d --name kpi-frontend \
  -p 80:80 \
  822824391150.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-frontend:latest
```

### Option B: Deploy with Docker Compose
```bash
# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  backend:
    image: 822824391150.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-backend:latest
    ports:
      - "5059:5059"
    environment:
      - FLASK_ENV=production
      - SQLALCHEMY_DATABASE_URI=sqlite:///instance/kpi_dashboard.db
      - OPENAI_API_KEY=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
    restart: unless-stopped

  frontend:
    image: 822824391150.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-frontend:latest
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
EOF

# Run with docker-compose
docker-compose up -d
```

## Step 4: Configure Networking

1. Go to **"Networking"** tab in Lightsail console
2. **Add rule** for port 80 (HTTP)
3. **Add rule** for port 5059 (Backend API)
4. **Add rule** for port 443 (HTTPS) - optional

## Step 5: Access Your Application

- **Frontend**: `http://your-instance-ip`
- **Backend API**: `http://your-instance-ip:5059`
- **Health Check**: `http://your-instance-ip:5059/api/accounts` (with X-Customer-ID header)

## Step 6: Set Up Custom Domain (Optional)

1. Go to **"Networking"** tab
2. Click **"Create DNS zone"**
3. Add your domain name
4. Update your domain's nameservers

## Cost Breakdown

- **Lightsail Instance**: $5-10/month
- **Data Transfer**: Included (1TB)
- **Storage**: Included (20-40 GB SSD)
- **Total**: ~$5-10/month

## Benefits

- ✅ No complex AWS permissions needed
- ✅ Simple Docker deployment
- ✅ Built-in load balancing
- ✅ Automatic backups
- ✅ Easy scaling
- ✅ Fixed pricing

## Monitoring

- **Instance metrics**: CPU, memory, network
- **Container logs**: `docker logs kpi-backend`
- **Application logs**: Available in Lightsail console
