#!/bin/bash

###############################################################################
# FULFILLMENT APP - AWS EC2 DEPLOYMENT SCRIPT
# Deploys alongside existing KPI application on same server
###############################################################################

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     FULFILLMENT APP - AWS DEPLOYMENT                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
APP_NAME="fulfillment"
APP_DIR="/var/www/fulfillment"
BACKEND_PORT=3001  # Different from KPI app (assumed to be on 3000)
FRONTEND_PORT=3002
NGINX_CONFIG="/etc/nginx/sites-available/fulfillment"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

print_step "Step 1: Installing dependencies..."

# Update package list
apt-get update

# Install Node.js if not already installed
if ! command -v node &> /dev/null; then
    print_step "Installing Node.js 20.x..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    print_success "Node.js installed: $(node -v)"
else
    print_success "Node.js already installed: $(node -v)"
fi

# Install PM2 if not already installed
if ! command -v pm2 &> /dev/null; then
    print_step "Installing PM2..."
    npm install -g pm2
    print_success "PM2 installed"
else
    print_success "PM2 already installed"
fi

# Install Nginx if not already installed
if ! command -v nginx &> /dev/null; then
    print_step "Installing Nginx..."
    apt-get install -y nginx
    systemctl enable nginx
    print_success "Nginx installed"
else
    print_success "Nginx already installed"
fi

# Install PostgreSQL if not already installed (for production database)
if ! command -v psql &> /dev/null; then
    print_step "Installing PostgreSQL..."
    apt-get install -y postgresql postgresql-contrib
    systemctl enable postgresql
    print_success "PostgreSQL installed"
else
    print_success "PostgreSQL already installed"
fi

print_step "Step 2: Creating application directory..."

# Create app directory if it doesn't exist
if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
    print_success "Directory created: $APP_DIR"
else
    print_success "Directory exists: $APP_DIR"
fi

# Create subdirectories
mkdir -p "$APP_DIR/backend"
mkdir -p "$APP_DIR/frontend"
mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/uploads"

print_success "Subdirectories created"

print_step "Step 3: Setting up PostgreSQL database..."

# Create database and user (skip if already exists)
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'fulfillment'" | grep -q 1 || \
sudo -u postgres psql << EOF
CREATE DATABASE fulfillment;
CREATE USER fulfillment_user WITH ENCRYPTED PASSWORD 'fulfillment_secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE fulfillment TO fulfillment_user;
\c fulfillment
GRANT ALL ON SCHEMA public TO fulfillment_user;
EOF

print_success "Database 'fulfillment' created"

print_step "Step 4: Configuring firewall..."

# Allow necessary ports
ufw allow $BACKEND_PORT/tcp
ufw allow $FRONTEND_PORT/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

print_success "Firewall configured"

print_step "Step 5: Creating Nginx configuration..."

# Create Nginx config for Fulfillment app
cat > "$NGINX_CONFIG" << 'NGINXCONF'
# Fulfillment App - Nginx Configuration
# Runs alongside KPI application

upstream fulfillment_backend {
    server 127.0.0.1:3001;
    keepalive 64;
}

upstream fulfillment_frontend {
    server 127.0.0.1:3002;
    keepalive 64;
}

# Main server block for Fulfillment app
server {
    listen 80;
    server_name fulfillment.yourdomain.com;  # Update with your domain

    # Redirect HTTP to HTTPS (after SSL setup)
    # return 301 https://$server_name$request_uri;

    # API endpoints
    location /api/fulfillment/ {
        proxy_pass http://fulfillment_backend/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # CORS headers
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
    }

    # Static files and frontend
    location /fulfillment/ {
        alias /var/www/fulfillment/frontend/build/;
        try_files $uri $uri/ /fulfillment/index.html;
        
        # Cache static assets
        location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }

    # Health check endpoint
    location /fulfillment/health {
        proxy_pass http://fulfillment_backend/health;
        access_log off;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss 
               application/json application/javascript;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/fulfillment_access.log;
    error_log /var/log/nginx/fulfillment_error.log;
}

# HTTPS configuration (uncomment after SSL setup)
# server {
#     listen 443 ssl http2;
#     server_name fulfillment.yourdomain.com;
#
#     ssl_certificate /etc/letsencrypt/live/fulfillment.yourdomain.com/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/fulfillment.yourdomain.com/privkey.pem;
#     ssl_protocols TLSv1.2 TLSv1.3;
#     ssl_ciphers HIGH:!aNULL:!MD5;
#
#     # ... (same location blocks as HTTP)
# }
NGINXCONF

# Enable the site
ln -sf "$NGINX_CONFIG" /etc/nginx/sites-enabled/fulfillment

# Test Nginx configuration
nginx -t

print_success "Nginx configured"

print_step "Step 6: Setting up SSL (Let's Encrypt)..."

print_warning "SSL setup requires:"
print_warning "1. A domain name pointing to this server"
print_warning "2. Run: sudo certbot --nginx -d fulfillment.yourdomain.com"
print_warning "3. Uncomment HTTPS block in Nginx config"

print_step "Step 7: Creating PM2 ecosystem file..."

cat > "$APP_DIR/ecosystem.config.js" << 'PM2CONFIG'
module.exports = {
  apps: [
    {
      name: 'fulfillment-backend',
      cwd: '/var/www/fulfillment/backend',
      script: 'server.js',
      instances: 2,
      exec_mode: 'cluster',
      env: {
        NODE_ENV: 'production',
        PORT: 3001,
        DB_HOST: 'localhost',
        DB_PORT: 5432,
        DB_NAME: 'fulfillment',
        DB_USER: 'fulfillment_user',
        DB_PASSWORD: 'fulfillment_secure_password_123',
        JWT_SECRET: 'your-super-secret-jwt-key-change-this',
        CORS_ORIGIN: 'https://fulfillment.yourdomain.com',
      },
      error_file: '/var/www/fulfillment/logs/backend-error.log',
      out_file: '/var/www/fulfillment/logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      max_memory_restart: '500M',
      watch: false,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
    },
    {
      name: 'fulfillment-frontend',
      cwd: '/var/www/fulfillment/frontend',
      script: 'npx',
      args: 'serve -s build -l 3002',
      instances: 1,
      env: {
        NODE_ENV: 'production',
      },
      error_file: '/var/www/fulfillment/logs/frontend-error.log',
      out_file: '/var/www/fulfillment/logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      autorestart: true,
    },
  ],
};
PM2CONFIG

print_success "PM2 ecosystem file created"

print_step "Step 8: Creating deployment helper scripts..."

# Create deploy script
cat > "$APP_DIR/deploy.sh" << 'DEPLOYSCRIPT'
#!/bin/bash
# Quick deployment script

set -e

APP_DIR="/var/www/fulfillment"
cd "$APP_DIR"

echo "🚀 Deploying Fulfillment App..."

# Pull latest code (if using git)
if [ -d ".git" ]; then
    echo "▶ Pulling latest code..."
    git pull origin main
fi

# Backend deployment
echo "▶ Deploying backend..."
cd "$APP_DIR/backend"
npm install --production
npm run migrate || echo "⚠ Migration failed or not configured"

# Frontend deployment
echo "▶ Deploying frontend..."
cd "$APP_DIR/frontend"
npm install
npm run build

# Restart services
echo "▶ Restarting services..."
pm2 restart fulfillment-backend
pm2 restart fulfillment-frontend

# Reload Nginx
echo "▶ Reloading Nginx..."
sudo nginx -t && sudo systemctl reload nginx

echo "✓ Deployment complete!"
pm2 status
DEPLOYSCRIPT

chmod +x "$APP_DIR/deploy.sh"

# Create backup script
cat > "$APP_DIR/backup.sh" << 'BACKUPSCRIPT'
#!/bin/bash
# Database backup script

BACKUP_DIR="/var/www/fulfillment/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/fulfillment_$DATE.sql"

mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup..."
sudo -u postgres pg_dump fulfillment > "$BACKUP_FILE"
gzip "$BACKUP_FILE"

echo "✓ Backup created: ${BACKUP_FILE}.gz"

# Keep only last 7 days
find "$BACKUP_DIR" -name "fulfillment_*.sql.gz" -mtime +7 -delete
echo "✓ Old backups cleaned"
BACKUPSCRIPT

chmod +x "$APP_DIR/backup.sh"

# Create status check script
cat > "$APP_DIR/status.sh" << 'STATUSSCRIPT'
#!/bin/bash
# Check application status

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          FULFILLMENT APP - STATUS CHECK                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "📊 PM2 Processes:"
pm2 list | grep fulfillment
echo ""

echo "🌐 Nginx Status:"
systemctl status nginx --no-pager | head -5
echo ""

echo "🗄️  PostgreSQL Status:"
systemctl status postgresql --no-pager | head -5
echo ""

echo "💾 Disk Usage:"
df -h /var/www/fulfillment
echo ""

echo "🔥 Recent Logs:"
echo "--- Backend ---"
tail -5 /var/www/fulfillment/logs/backend-out.log
echo ""
echo "--- Frontend ---"
tail -5 /var/www/fulfillment/logs/frontend-out.log
echo ""

echo "🌍 API Health Check:"
curl -s http://localhost:3001/health || echo "Backend not responding"
echo ""
STATUSSCRIPT

chmod +x "$APP_DIR/status.sh"

print_success "Helper scripts created"

print_step "Step 9: Setting permissions..."

# Set ownership
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"
chmod -R 775 "$APP_DIR/logs"
chmod -R 775 "$APP_DIR/uploads"

print_success "Permissions set"

print_step "Step 10: Restarting services..."

# Restart Nginx
systemctl restart nginx

print_success "Nginx restarted"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          DEPLOYMENT SETUP COMPLETE!                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
print_success "Application directory: $APP_DIR"
print_success "Backend port: $BACKEND_PORT"
print_success "Frontend port: $FRONTEND_PORT"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "1. Copy your application files to $APP_DIR:"
echo "   scp -r backend/ user@server:$APP_DIR/"
echo "   scp -r frontend/ user@server:$APP_DIR/"
echo ""
echo "2. Install dependencies:"
echo "   cd $APP_DIR/backend && npm install"
echo "   cd $APP_DIR/frontend && npm install && npm run build"
echo ""
echo "3. Run database migrations:"
echo "   cd $APP_DIR/backend && npm run migrate"
echo ""
echo "4. Start PM2 processes:"
echo "   pm2 start $APP_DIR/ecosystem.config.js"
echo "   pm2 save"
echo "   pm2 startup"
echo ""
echo "5. Setup SSL certificate:"
echo "   sudo apt-get install certbot python3-certbot-nginx"
echo "   sudo certbot --nginx -d fulfillment.yourdomain.com"
echo ""
echo "6. Configure DNS:"
echo "   Point fulfillment.yourdomain.com to this server's IP"
echo ""
echo "📚 Helpful commands:"
echo "   $APP_DIR/deploy.sh      - Deploy new version"
echo "   $APP_DIR/backup.sh      - Backup database"
echo "   $APP_DIR/status.sh      - Check application status"
echo "   pm2 logs fulfillment    - View logs"
echo "   pm2 monit               - Monitor processes"
echo ""

