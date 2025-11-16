#!/bin/bash

###############################################################################
# FULFILLMENT APP - DOCKER DEPLOYMENT SCRIPT
# Deploy to EC2 using Docker
###############################################################################

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     FULFILLMENT APP - DOCKER DEPLOYMENT                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

print_step "Step 1: Installing Docker..."

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $SUDO_USER
    print_success "Docker installed"
else
    print_success "Docker already installed: $(docker --version)"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose installed"
else
    print_success "Docker Compose already installed: $(docker-compose --version)"
fi

print_step "Step 2: Creating application directory..."

APP_DIR="/opt/fulfillment"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

print_success "Directory created: $APP_DIR"

print_step "Step 3: Setting up environment..."

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cat > .env << 'ENVFILE'
DB_PASSWORD=fulfillment_prod_password_change_this
JWT_SECRET=change-this-to-a-secure-random-string-min-32-chars
CORS_ORIGIN=https://fulfillment.yourdomain.com
ENVFILE
    print_success "Created .env file (IMPORTANT: Update passwords!)"
    print_warning "Edit $APP_DIR/.env with secure passwords before starting"
else
    print_success ".env file exists"
fi

print_step "Step 4: Creating backup directory..."

mkdir -p "$APP_DIR/backups"
print_success "Backup directory created"

print_step "Step 5: Setting up log rotation..."

cat > /etc/logrotate.d/fulfillment << 'LOGROTATE'
/opt/fulfillment/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
}
LOGROTATE

print_success "Log rotation configured"

print_step "Step 6: Creating helper scripts..."

# Backup script
cat > "$APP_DIR/backup.sh" << 'BACKUPSCRIPT'
#!/bin/bash
BACKUP_DIR="/opt/fulfillment/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/fulfillment_$DATE.sql"

echo "📦 Creating database backup..."
docker exec fulfillment-db-prod pg_dump -U fulfillment_user fulfillment > "$BACKUP_FILE"
gzip "$BACKUP_FILE"

echo "✓ Backup created: ${BACKUP_FILE}.gz"

# Keep only last 7 days
find "$BACKUP_DIR" -name "fulfillment_*.sql.gz" -mtime +7 -delete
echo "✓ Old backups cleaned"
BACKUPSCRIPT

chmod +x "$APP_DIR/backup.sh"

# Status script
cat > "$APP_DIR/status.sh" << 'STATUSSCRIPT'
#!/bin/bash
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          FULFILLMENT APP - DOCKER STATUS                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "📦 Docker Containers:"
docker ps --filter "name=fulfillment" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "💾 Docker Volumes:"
docker volume ls --filter "name=fulfillment"
echo ""

echo "🌐 Health Checks:"
echo "Backend: $(curl -s http://localhost:3001/health | jq -r '.status' 2>/dev/null || echo 'Not responding')"
echo "Frontend: $(curl -s http://localhost:3002/health 2>/dev/null && echo 'OK' || echo 'Not responding')"
echo ""

echo "📊 Resource Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker ps --filter "name=fulfillment" -q)
STATUSSCRIPT

chmod +x "$APP_DIR/status.sh"

# Deploy script
cat > "$APP_DIR/deploy.sh" << 'DEPLOYSCRIPT'
#!/bin/bash
set -e

echo "🚀 Deploying Fulfillment App..."

cd /opt/fulfillment

# Pull latest images
echo "▶ Pulling latest code..."
if [ -d ".git" ]; then
    git pull origin main
fi

# Build images
echo "▶ Building Docker images..."
docker-compose -f docker-compose.prod.yml build

# Stop old containers
echo "▶ Stopping old containers..."
docker-compose -f docker-compose.prod.yml down

# Start new containers
echo "▶ Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services
echo "▶ Waiting for services..."
sleep 10

# Check health
echo "▶ Health check..."
curl -f http://localhost:3001/health || echo "⚠ Backend not healthy"
curl -f http://localhost:3002/health || echo "⚠ Frontend not healthy"

echo "✓ Deployment complete!"
docker ps --filter "name=fulfillment"
DEPLOYSCRIPT

chmod +x "$APP_DIR/deploy.sh"

print_success "Helper scripts created"

print_step "Step 7: Configuring firewall..."

# Allow necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 3001/tcp
ufw allow 3002/tcp
ufw --force enable

print_success "Firewall configured"

print_step "Step 8: Setting up auto-start..."

# Create systemd service
cat > /etc/systemd/system/fulfillment.service << 'SYSTEMD'
[Unit]
Description=Fulfillment App
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/fulfillment
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable fulfillment.service

print_success "Auto-start configured"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          DOCKER SETUP COMPLETE!                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
print_success "Application directory: $APP_DIR"
print_success "Environment file: $APP_DIR/.env"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Copy your application files to $APP_DIR:"
echo "   scp -r * user@server:$APP_DIR/"
echo ""
echo "2. Update .env with secure passwords:"
echo "   nano $APP_DIR/.env"
echo ""
echo "3. Start the application:"
echo "   cd $APP_DIR"
echo "   docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "4. Check status:"
echo "   $APP_DIR/status.sh"
echo ""
echo "5. Setup SSL:"
echo "   docker run -it --rm -v /etc/letsencrypt:/etc/letsencrypt certbot/certbot certonly --standalone -d fulfillment.yourdomain.com"
echo ""
echo "📚 Helpful commands:"
echo "   $APP_DIR/deploy.sh      - Deploy new version"
echo "   $APP_DIR/backup.sh      - Backup database"
echo "   $APP_DIR/status.sh      - Check status"
echo "   docker logs -f fulfillment-backend-prod  - View logs"
echo "   docker-compose -f docker-compose.prod.yml down  - Stop all"
echo ""

