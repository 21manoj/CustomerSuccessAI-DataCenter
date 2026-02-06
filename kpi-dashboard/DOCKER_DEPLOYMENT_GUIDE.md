# 🐳 KPI Dashboard - Docker Deployment Guide (Separate Machine)

Step-by-step guide to deploy kpi-dashboard on a separate machine with Docker and PostgreSQL.

---

## 📋 Prerequisites

- **Server**: Ubuntu 20.04+ / Amazon Linux 2 / Debian 11+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Ports**: 80 (frontend), 5059 (backend), 5432 (postgres - optional external)
- **Disk**: 10GB+ free space

---

## 🔧 Step 1: Install Docker & Docker Compose

### On Ubuntu/Debian:
```bash
# Update packages
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# Add user to docker group (optional, to avoid sudo)
sudo usermod -aG docker $USER
# Log out and back in for group to take effect
```

### On Amazon Linux 2:
```bash
# Install Docker
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

---

## 📦 Step 2: Clone/Upload Project Files

### Option A: Git Clone
```bash
cd /opt
sudo git clone <your-repo-url> kpi-dashboard
cd kpi-dashboard
```

### Option B: Upload via SCP
```bash
# On your local machine
tar -czf kpi-dashboard.tar.gz kpi-dashboard/
scp kpi-dashboard.tar.gz user@your-server-ip:/home/user/

# On server
cd /opt
sudo mkdir kpi-dashboard
sudo tar -xzf ~/kpi-dashboard.tar.gz -C kpi-dashboard --strip-components=1
cd kpi-dashboard
```

---

## 🗄️ Step 3: Create Docker Compose with PostgreSQL

Create/update `docker-compose.yml`:

```bash
cd /opt/kpi-dashboard
nano docker-compose.yml
```

Paste this configuration:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: kpi-dashboard-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: kpi_dashboard
      POSTGRES_USER: kpi_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - kpi-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kpi_user -d kpi_dashboard"]
      interval: 10s
      timeout: 5s
      retries: 5
    # Remove ports section if you don't need external access
    # ports:
    #   - "5432:5432"

  # Backend Service
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: kpi-dashboard-backend
    ports:
      - "5059:5059"
    env_file:
      - docker.env
    environment:
      - FLASK_APP=app.py
      - FLASK_ENV=production
      - PYTHONPATH=/app
      - DATABASE_URL=postgresql://kpi_user:${DB_PASSWORD}@postgres:5432/kpi_dashboard
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/qdrant_storage:/app/qdrant_storage
      - ./backend/.env:/app/.env:ro
    networks:
      - kpi-network
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5059/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Frontend Service
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.nginx
    container_name: kpi-dashboard-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    networks:
      - kpi-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

networks:
  kpi-network:
    driver: bridge

volumes:
  postgres_data:
    driver: local
  qdrant_data:
    driver: local
```

Save and exit (`Ctrl+X`, `Y`, `Enter`).

---

## 🔐 Step 4: Configure Environment Variables

Create `docker.env` file:

```bash
nano docker.env
```

Add these variables (adjust values):

```bash
# Database
DB_PASSWORD=your_strong_password_here

# Flask
SECRET_KEY=generate_with_python_-c_"import_secrets;print(secrets.token_hex(32))"
FLASK_ENV=production

# OpenAI (if using RAG)
OPENAI_API_KEY=your_openai_api_key_here

# Qdrant (if using remote)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_key_if_needed
```

**Generate SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Set secure permissions:
```bash
chmod 600 docker.env
```

---

## 🏗️ Step 5: Build and Start Services

```bash
cd /opt/kpi-dashboard

# Build images (first time - takes 5-10 minutes)
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Expected output:**
```
NAME                      STATUS
kpi-dashboard-postgres    Up (healthy)
kpi-dashboard-backend     Up (healthy)
kpi-dashboard-frontend    Up (healthy)
```

---

## ✅ Step 6: Initialize Database

```bash
# Run database migrations
docker-compose exec backend flask db upgrade

# Or if you have a setup script
docker-compose exec backend python setup_database.py
```

---

## 🔍 Step 7: Verify Deployment

### Check Services:
```bash
# Check all containers
docker-compose ps

# Check logs
docker-compose logs backend
docker-compose logs postgres

# Test backend health
curl http://localhost:5059/

# Test frontend
curl http://localhost/
```

### Access the Application:
- **Frontend**: `http://your-server-ip`
- **Backend API**: `http://your-server-ip:5059`

---

## 🔧 Common Commands

### Start/Stop:
```bash
docker-compose up -d        # Start all services
docker-compose stop         # Stop services
docker-compose down         # Stop and remove containers
docker-compose restart      # Restart all services
```

### Logs:
```bash
docker-compose logs -f              # All logs
docker-compose logs -f backend      # Backend only
docker-compose logs -f postgres     # Database only
```

### Database:
```bash
# Access PostgreSQL shell
docker-compose exec postgres psql -U kpi_user -d kpi_dashboard

# Backup database
docker-compose exec postgres pg_dump -U kpi_user kpi_dashboard > backup.sql

# Restore database
docker-compose exec -T postgres psql -U kpi_user kpi_dashboard < backup.sql
```

### Updates:
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d
```

---

## 🔒 Security Recommendations

1. **Firewall** (UFW on Ubuntu):
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 5059/tcp
   sudo ufw enable
   ```

2. **Remove external PostgreSQL port** (if not needed):
   - Remove `ports` section from postgres service in docker-compose.yml

3. **Use strong passwords** in `docker.env`

4. **SSL/HTTPS** (production):
   - Use Nginx reverse proxy with Let's Encrypt
   - Set `SESSION_COOKIE_SECURE=true` in environment

---

## 🐛 Troubleshooting

### Database connection errors:
```bash
# Check postgres is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Test connection
docker-compose exec backend python -c "from extensions import db; print(db.engine.url)"
```

### Backend won't start:
```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Port conflicts:
```bash
# Check what's using ports
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :5059
sudo netstat -tulpn | grep :5432

# Change ports in docker-compose.yml if needed
```

---

## 📊 Monitoring

### Check resource usage:
```bash
docker stats
```

### Check disk space:
```bash
docker system df
```

---

## ✅ Done!

Your kpi-dashboard is now running on the separate machine with:
- ✅ PostgreSQL in Docker
- ✅ Backend API (port 5059)
- ✅ Frontend (port 80)
- ✅ Persistent data volumes
- ✅ Auto-restart on failure


