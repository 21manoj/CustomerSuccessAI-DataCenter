# Qdrant Remote Setup Guide

**Date**: January 2, 2026

---

## Overview

This guide explains how to run Qdrant on a remote compute node and connect your application to it remotely. This is useful when:
- Docker requires too many system resources on your local machine
- You want to use a dedicated server for vector database operations
- You need better performance or scalability

---

## Remote Qdrant Setup

### Step 1: Set Up Qdrant on Remote Node

On your remote compute node, you have two options:

#### Option A: Using Docker (Recommended)

1. **SSH into your remote node:**
   ```bash
   ssh user@remote-node-ip
   ```

2. **Install Docker** (if not already installed):
   ```bash
   # For Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   ```

3. **Start Qdrant with remote access:**
   ```bash
   # Create storage directory
   mkdir -p ~/qdrant_storage
   
   # Run Qdrant container with network binding
   docker run -d \
     --name qdrant-server \
     -p 0.0.0.0:6333:6333 \
     -p 0.0.0.0:6334:6334 \
     -v ~/qdrant_storage:/qdrant/storage \
     qdrant/qdrant:latest
   ```

   **Important**: Using `0.0.0.0` instead of `127.0.0.1` allows external connections.

4. **Verify Qdrant is running:**
   ```bash
   curl http://localhost:6333/health
   ```

5. **Configure firewall** (if needed):
   ```bash
   # Allow Qdrant ports (adjust based on your firewall)
   sudo ufw allow 6333/tcp
   sudo ufw allow 6334/tcp
   ```

#### Option B: Using Qdrant Binary

1. **Download Qdrant binary:**
   ```bash
   wget https://github.com/qdrant/qdrant/releases/download/v1.7.0/qdrant-x86_64-unknown-linux-gnu.tar.gz
   tar -xzf qdrant-x86_64-unknown-linux-gnu.tar.gz
   ```

2. **Create config file** (`qdrant_config.yaml`):
   ```yaml
   service:
     host: 0.0.0.0  # Listen on all interfaces
     http_port: 6333
     grpc_port: 6334
   
   storage:
     storage_path: ./qdrant_storage
   ```

3. **Run Qdrant:**
   ```bash
   ./qdrant --config-path qdrant_config.yaml
   ```

---

## Step 2: Configure Your Application

### Update Environment Variables

In your local application (where the Flask backend runs), set these environment variables:

#### Option 1: Update `.env` file

Edit `kpi-dashboard/backend/.env`:

```bash
# Qdrant Remote Connection
QDRANT_HOST=your-remote-node-ip-or-hostname
QDRANT_PORT=6333

# Optional: If using Qdrant Cloud or authenticated instance
# QDRANT_API_KEY=your-api-key-here
```

**Example:**
```bash
QDRANT_HOST=192.168.1.100
QDRANT_PORT=6333
```

Or if using a hostname:
```bash
QDRANT_HOST=qdrant.example.com
QDRANT_PORT=6333
```

#### Option 2: Set Environment Variables Directly

```bash
export QDRANT_HOST=your-remote-node-ip
export QDRANT_PORT=6333
```

#### Option 3: Use Docker Compose or Systemd

If you're using Docker Compose, add to your `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - QDRANT_HOST=your-remote-node-ip
      - QDRANT_PORT=6333
```

---

## Step 3: Test Remote Connection

### Test from Your Local Machine

```bash
# Test HTTP connection
curl http://your-remote-node-ip:6333/health

# Should return: {"status":"ok"}
```

### Test from Python

```bash
cd kpi-dashboard/backend
python3 -c "
from qdrant_client import QdrantClient
import os
os.environ['QDRANT_HOST'] = 'your-remote-node-ip'
os.environ['QDRANT_PORT'] = '6333'

client = QdrantClient(
    host=os.getenv('QDRANT_HOST'),
    port=int(os.getenv('QDRANT_PORT'))
)
collections = client.get_collections()
print(f'✅ Connected! Found {len(collections.collections)} collections')
"
```

---

## Step 4: Security Considerations

### 1. Network Security

**For Development:**
- Use VPN or private network
- Restrict access with firewall rules

**For Production:**
- Use TLS/SSL (Qdrant supports HTTPS)
- Implement authentication (Qdrant Cloud or custom auth)
- Use firewall rules to restrict access

### 2. Enable TLS (Optional but Recommended)

If you need encrypted connections:

1. **On Remote Node**, update Qdrant config:
   ```yaml
   service:
     host: 0.0.0.0
     http_port: 6333
     grpc_port: 6334
     enable_tls: true
     cert_path: /path/to/cert.pem
     key_path: /path/to/key.pem
   ```

2. **In Your App**, use HTTPS:
   ```python
   QdrantClient(
       url="https://your-remote-node-ip:6333",
       api_key="your-api-key"  # if using authentication
   )
   ```

### 3. Firewall Configuration

**On Remote Node:**
```bash
# Allow only specific IPs (recommended)
sudo ufw allow from your-app-server-ip to any port 6333
sudo ufw allow from your-app-server-ip to any port 6334

# Or allow from specific network
sudo ufw allow from 192.168.1.0/24 to any port 6333
```

---

## Step 5: Restart Your Application

After updating environment variables:

```bash
# Restart Flask backend
cd kpi-dashboard/backend
# Kill existing process
lsof -ti:8005 | xargs kill -9

# Restart with new environment
nohup python3 -m flask --app app_v3_minimal run --port 8005 --host 0.0.0.0 --debug > /tmp/flask_backend.log 2>&1 &
```

Check logs to verify connection:
```bash
tail -f /tmp/flask_backend.log | grep -i qdrant
```

You should see:
```
✅ Connected to Qdrant server
```

---

## Troubleshooting

### Connection Refused

**Problem:** `Connection refused` error

**Solutions:**
1. Check Qdrant is running on remote node:
   ```bash
   ssh user@remote-node "docker ps | grep qdrant"
   ```

2. Verify Qdrant is listening on all interfaces:
   ```bash
   ssh user@remote-node "netstat -tlnp | grep 6333"
   # Should show: 0.0.0.0:6333 (not 127.0.0.1:6333)
   ```

3. Check firewall rules:
   ```bash
   ssh user@remote-node "sudo ufw status"
   ```

4. Test network connectivity:
   ```bash
   telnet your-remote-node-ip 6333
   # Or
   nc -zv your-remote-node-ip 6333
   ```

### Timeout Errors

**Problem:** Connection timeout

**Solutions:**
1. Check network routing
2. Verify firewall allows traffic
3. Check if remote node is accessible:
   ```bash
   ping your-remote-node-ip
   ```

### Authentication Errors

**Problem:** Authentication required

**Solutions:**
1. If using Qdrant Cloud, set `QDRANT_API_KEY`:
   ```bash
   export QDRANT_API_KEY=your-api-key
   ```

2. Update connection code to use API key (if needed)

---

## Environment Variable Reference

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `QDRANT_HOST` | Remote Qdrant server hostname or IP | `localhost` | `192.168.1.100` |
| `QDRANT_PORT` | Qdrant HTTP port | `6333` | `6333` |
| `QDRANT_API_KEY` | API key for authentication (optional) | None | `your-api-key` |
| `QDRANT_COLLECTION` | Base collection name | `kpi_dashboard_vectors` | `my_vectors` |

---

## Quick Start Checklist

- [ ] Qdrant running on remote node
- [ ] Qdrant accessible from your network (test with `curl`)
- [ ] Firewall configured (if needed)
- [ ] Environment variables set (`QDRANT_HOST`, `QDRANT_PORT`)
- [ ] Application restarted
- [ ] Connection verified in logs

---

## Example: Complete Remote Setup

**Remote Node (192.168.1.100):**
```bash
# Start Qdrant
docker run -d \
  --name qdrant-server \
  -p 0.0.0.0:6333:6333 \
  -p 0.0.0.0:6334:6334 \
  -v ~/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Verify
curl http://localhost:6333/health
```

**Local Application:**
```bash
# Set environment
export QDRANT_HOST=192.168.1.100
export QDRANT_PORT=6333

# Test connection
curl http://192.168.1.100:6333/health

# Restart app
# (restart Flask backend)
```

---

## Additional Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant Docker Setup](https://qdrant.tech/documentation/guides/installation/)
- [Qdrant Cloud](https://cloud.qdrant.io/) (Managed Qdrant service)
