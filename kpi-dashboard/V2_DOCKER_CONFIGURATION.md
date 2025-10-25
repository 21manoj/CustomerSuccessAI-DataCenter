# V2 Docker Configuration

## Overview

V2 deployment uses a **2-container architecture** with separate frontend (Nginx) and backend (Flask) containers, connected via a dedicated Docker network.

---

## Container Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS EC2 Instance                          │
│                      3.84.178.121                                │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Host Nginx (Port 80/443)                      │  │
│  │  • SSL Termination                                         │  │
│  │  • HTTPS → HTTP proxy                                      │  │
│  │  • Domain: customervaluesystem.triadpartners.ai            │  │
│  └────────────────────────────────────────────────────────────┘  │
│           │                                 │                     │
│           │ Port 3001                       │ Port 8080           │
│           ▼                                 ▼                     │
│  ┌─────────────────────┐         ┌─────────────────────┐        │
│  │  V2 Frontend        │         │  V2 Backend         │        │
│  │  Container          │────────>│  Container          │        │
│  │                     │  API    │                     │        │
│  │  kpi-dashboard-     │  Proxy  │  kpi-dashboard-v2   │        │
│  │  frontend-v2        │         │                     │        │
│  │                     │         │                     │        │
│  │  • Nginx Alpine     │         │  • Python 3.11      │        │
│  │  • React SPA        │         │  • Flask API        │        │
│  │  • Port: 80→3001    │         │  • Port: 8080       │        │
│  └─────────────────────┘         └─────────────────────┘        │
│           │                                 │                     │
│           └─────────────┬───────────────────┘                     │
│                         │                                         │
│                  ┌──────▼──────┐                                 │
│                  │ Docker      │                                 │
│                  │ Network:    │                                 │
│                  │ kpi-network-│                                 │
│                  │ v2          │                                 │
│                  └─────────────┘                                 │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Persistent Storage                            │  │
│  │  /home/ec2-user/kpi-dashboard-v2/instance                  │  │
│  │  • Database: kpi_dashboard.db (SQLite)                     │  │
│  │  • Mounted to: /app/instance in backend container          │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Containers

### 1. Backend Container: `kpi-dashboard-v2`

**Image:** `kpi-dashboard:v2-8080`  
**Base:** `python:3.11-slim`  
**Size:** ~8.13 GB  
**Status:** Running, restart=unless-stopped

**Configuration:**
```yaml
Container Name: kpi-dashboard-v2
Image: kpi-dashboard:v2-8080
Network: kpi-network-v2 (172.24.0.2)
Ports: 0.0.0.0:8080 → 8080/tcp
Restart Policy: unless-stopped
```

**Volumes:**
```yaml
Host: /home/ec2-user/kpi-dashboard-v2/instance
Container: /app/instance
Type: bind mount (read-write)
Purpose: Persistent database storage
```

**Environment Variables:**
```bash
FLASK_ENV=production
PYTHON_VERSION=3.11.14
PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
LANG=C.UTF-8
```

**Entry Point:**
```bash
CMD ["python", "run_server_v2.py"]
```

---

### 2. Frontend Container: `kpi-dashboard-frontend-v2`

**Image:** `kpi-dashboard-frontend:v2`  
**Base:** `nginx:alpine`  
**Size:** ~56 MB  
**Status:** Running, restart=unless-stopped

**Configuration:**
```yaml
Container Name: kpi-dashboard-frontend-v2
Image: kpi-dashboard-frontend:v2
Network: kpi-network-v2 (172.24.0.3)
Ports: 0.0.0.0:3001 → 80/tcp
Restart Policy: unless-stopped
```

**No Volumes:** Static files built into image

**Entry Point:**
```bash
CMD ["nginx", "-g", "daemon off;"]
```

---

## Docker Network

**Network Name:** `kpi-network-v2`  
**Driver:** bridge  
**Subnet:** 172.24.0.0/16

**Connected Containers:**
- `kpi-dashboard-v2` (172.24.0.2)
- `kpi-dashboard-frontend-v2` (172.24.0.3)

**Inter-Container Communication:**
Frontend → Backend via `http://kpi-dashboard-v2:8080`

---

## Dockerfiles

### Backend Dockerfile (`Dockerfile.v2`)

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/
COPY build/ /app/static/

RUN mkdir -p /app/instance

EXPOSE 8080

CMD ["python", "run_server_v2.py"]
```

**Build Command:**
```bash
docker build -f Dockerfile.v2 -t kpi-dashboard:v2-8080 .
```

**Key Features:**
- ✅ Python 3.11 slim base (smaller footprint)
- ✅ Installs gcc/g++ for native dependencies
- ✅ Copies backend code and React build
- ✅ Creates instance directory for database
- ✅ Exposes port 8080

---

### Frontend Dockerfile (`Dockerfile.nginx.v2`)

```dockerfile
FROM nginx:alpine

# Copy React build
COPY build/ /usr/share/nginx/html/

# Copy nginx config
COPY nginx.v2.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**Build Command:**
```bash
docker build -f Dockerfile.nginx.v2 -t kpi-dashboard-frontend:v2 .
```

**Key Features:**
- ✅ Nginx Alpine (minimal size ~56MB)
- ✅ Serves React static files
- ✅ Custom nginx config for API proxy
- ✅ React Router support

---

## Nginx Configuration

### Container Nginx (`nginx.v2.conf`)

Located inside the frontend container:

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    server {
        listen 80;
        server_name _;
        root /usr/share/nginx/html;
        index index.html;

        # Serve static files
        location /static/ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Proxy API requests to V2 backend by container name
        location /api/ {
            proxy_pass http://kpi-dashboard-v2:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # React Router - serve index.html for all routes
        location / {
            try_files $uri $uri/ /index.html;
        }
    }
}
```

**Key Features:**
- ✅ API proxy to backend container by name (`kpi-dashboard-v2:8080`)
- ✅ Static file caching (1 year)
- ✅ React Router support (SPA)
- ✅ Proper headers forwarding

---

### Host Nginx (`/etc/nginx/conf.d/customervaluesystem.conf`)

Located on EC2 host (outside containers):

```nginx
server {
    listen 80;
    server_name customervaluesystem.triadpartners.ai;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all HTTP traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name customervaluesystem.triadpartners.ai;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/customervaluesystem.triadpartners.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/customervaluesystem.triadpartners.ai/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Proxy to V2 frontend
    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Proxy API calls to V2 backend
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Key Features:**
- ✅ SSL termination
- ✅ HTTP → HTTPS redirect
- ✅ TLS 1.2/1.3
- ✅ Let's Encrypt certificate
- ✅ Proxies to container ports

---

## Backend Server Script

**File:** `backend/run_server_v2.py`

```python
#!/usr/bin/env python3
"""V2 Server on port 8080 (browser-safe port)"""
from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("Starting KPI Dashboard V2")
    print("Port: 8080 (browser-safe)")
    print("Version: 2.0.0")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8080, debug=False)
```

**Features:**
- ✅ Runs on port 8080 (browser-safe)
- ✅ Binds to all interfaces (0.0.0.0)
- ✅ Production mode (debug=False)

---

## Docker Commands

### Build Images

```bash
# Backend
cd /home/ec2-user/kpi-dashboard-v2
sudo docker build -f Dockerfile.v2 -t kpi-dashboard:v2-8080 .

# Frontend
sudo docker build -f Dockerfile.nginx.v2 -t kpi-dashboard-frontend:v2 .
```

### Create Network

```bash
sudo docker network create kpi-network-v2
```

### Run Containers

**Backend:**
```bash
sudo docker run -d \
  --name kpi-dashboard-v2 \
  --network kpi-network-v2 \
  -p 8080:8080 \
  -v /home/ec2-user/kpi-dashboard-v2/instance:/app/instance \
  -v /home/ec2-user/kpi-dashboard-v2/uploads:/app/uploads \
  -e FLASK_ENV=production \
  --restart unless-stopped \
  kpi-dashboard:v2-8080
```

**Frontend:**
```bash
sudo docker run -d \
  --name kpi-dashboard-frontend-v2 \
  --network kpi-network-v2 \
  -p 3001:80 \
  --restart unless-stopped \
  kpi-dashboard-frontend:v2
```

### Management Commands

```bash
# View containers
sudo docker ps | grep v2

# View logs
sudo docker logs -f kpi-dashboard-v2
sudo docker logs -f kpi-dashboard-frontend-v2

# Restart containers
sudo docker restart kpi-dashboard-v2
sudo docker restart kpi-dashboard-frontend-v2

# Stop containers
sudo docker stop kpi-dashboard-v2 kpi-dashboard-frontend-v2

# Remove containers
sudo docker rm kpi-dashboard-v2 kpi-dashboard-frontend-v2

# View network
sudo docker network inspect kpi-network-v2

# Execute commands in container
sudo docker exec -it kpi-dashboard-v2 bash
sudo docker exec kpi-dashboard-v2 python -c "from app import app, db; ..."
```

---

## Port Mapping

| Service | Container Port | Host Port | Public Access |
|---------|---------------|-----------|---------------|
| V2 Backend | 8080 | 8080 | http://3.84.178.121:8080 |
| V2 Frontend | 80 | 3001 | http://3.84.178.121:3001 |
| V2 HTTPS | - | 443 | https://customervaluesystem.triadpartners.ai |
| V2 HTTP Redirect | - | 80 | http://customervaluesystem.triadpartners.ai → HTTPS |

---

## Data Persistence

### Database Location

**Host:** `/home/ec2-user/kpi-dashboard-v2/instance/kpi_dashboard.db`  
**Container:** `/app/instance/kpi_dashboard.db`  
**Type:** SQLite  
**Size:** ~50 MB (varies with data)

**Backup:**
```bash
# Backup database
sudo docker exec kpi-dashboard-v2 cp /app/instance/kpi_dashboard.db /app/instance/kpi_dashboard.db.backup

# Copy to host
sudo docker cp kpi-dashboard-v2:/app/instance/kpi_dashboard.db ./kpi_dashboard_v2_backup.db
```

### Uploads Location

**Host:** `/home/ec2-user/kpi-dashboard-v2/uploads/`  
**Container:** `/app/uploads/`  
**Contains:** Uploaded Excel files, master files

---

## Container Isolation

### V1 vs V2 Separation

| Aspect | V1 | V2 |
|--------|----|----|
| Network | ec2-user_kpi-network | kpi-network-v2 |
| Frontend Port | 3000 | 3001 |
| Backend Port | 5059 | 8080 |
| Domain | customersuccessai.triadpartners.ai | customervaluesystem.triadpartners.ai |
| Database | Separate instance | Separate instance |
| Containers | kpi-dashboard-frontend, kpi-dashboard-backend | kpi-dashboard-frontend-v2, kpi-dashboard-v2 |

**No Shared Resources:**
- ✅ Separate Docker networks
- ✅ Separate databases
- ✅ Separate ports
- ✅ Can run simultaneously
- ✅ Independent restart/update

---

## Health Checks

### Container Health

```bash
# Check if containers are running
sudo docker ps | grep v2

# Check backend health
curl http://localhost:8080/api/health

# Check frontend health
curl http://localhost:3001/

# Check container logs
sudo docker logs --tail 50 kpi-dashboard-v2
```

### Database Health

```bash
# Execute SQL in container
sudo docker exec kpi-dashboard-v2 python << EOF
from app import app, db
with app.app_context():
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Tables: {db.engine.table_names()}")
EOF
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
sudo docker logs kpi-dashboard-v2

# Check if port is in use
sudo netstat -tlnp | grep 8080

# Remove and recreate
sudo docker stop kpi-dashboard-v2
sudo docker rm kpi-dashboard-v2
# Run docker run command again
```

### Database Issues

```bash
# Check database file exists
sudo docker exec kpi-dashboard-v2 ls -lh /app/instance/

# Check database permissions
sudo docker exec kpi-dashboard-v2 python -c "from app import app; print(app.config['SQLALCHEMY_DATABASE_URI'])"

# Run migrations
sudo docker exec kpi-dashboard-v2 flask db upgrade
```

### Network Issues

```bash
# Check network exists
sudo docker network ls | grep v2

# Inspect network
sudo docker network inspect kpi-network-v2

# Recreate network
sudo docker network rm kpi-network-v2
sudo docker network create kpi-network-v2
# Recreate containers with new network
```

---

## Comparison: V1 vs V2 Docker Setup

| Feature | V1 | V2 |
|---------|----|----|
| **Architecture** | 2 containers | 2 containers |
| **Backend Image** | ec2-user-backend | kpi-dashboard:v2-8080 |
| **Frontend Image** | ec2-user-frontend | kpi-dashboard-frontend:v2 |
| **Backend Size** | ~8 GB | ~8.13 GB |
| **Frontend Size** | ~56 MB | ~56 MB |
| **Network** | ec2-user_kpi-network | kpi-network-v2 |
| **Restart Policy** | unless-stopped | unless-stopped |
| **Data Persistence** | Volume mounts | Volume mounts |
| **SSL** | Let's Encrypt | Let's Encrypt |

**Both use the same design pattern!**

---

## Best Practices

✅ **Implemented:**
- Separate containers for frontend/backend
- Dedicated Docker network
- Volume mounts for persistence
- Restart policy for high availability
- Minimal base images (Alpine for frontend)
- Environment-based configuration
- SSL termination at host level
- Health checks and logging

✅ **Security:**
- Non-root user in containers
- Minimal attack surface (slim images)
- No unnecessary packages
- Network isolation
- SSL/TLS encryption

✅ **Performance:**
- Nginx for static file serving
- Cached static assets
- Persistent database storage
- Efficient image layers

---

**Created:** October 15, 2025  
**Version:** V2 Production  
**Status:** Running  
**Uptime:** Since deployment (auto-restart enabled)

