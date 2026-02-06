# Qdrant Vector Database Startup

**Date**: January 1, 2026

---

## Overview

Qdrant vector database is now integrated into the startup process. All AI agents moving forward will use Qdrant for vector database operations.

---

## Starting Qdrant

### Option 1: Start Qdrant Only
```bash
cd kpi-dashboard/backend
./start_qdrant.sh
```

### Option 2: Start Qdrant + Backend Together (Recommended)
```bash
cd kpi-dashboard/backend
./start_backend_with_qdrant.sh
```

This script will:
1. Start Qdrant container (if not running)
2. Wait for Qdrant to be ready
3. Run startup checks
4. Start the backend server

---

## Qdrant Configuration

- **Port**: 6333 (HTTP), 6334 (gRPC)
- **Container Name**: `qdrant-server`
- **Storage**: `./qdrant_storage` (persistent)
- **Image**: `qdrant/qdrant:latest`

### Environment Variables
- `QDRANT_HOST`: localhost (default)
- `QDRANT_PORT`: 6333 (default)

---

## Verification

### Check if Qdrant is running:
```bash
docker ps | grep qdrant
curl http://localhost:6333/health
```

### Access Qdrant Dashboard:
```
http://localhost:6333/dashboard
```

---

## Stopping Qdrant

```bash
docker stop qdrant-server
```

To remove the container:
```bash
docker stop qdrant-server
docker rm qdrant-server
```

---

## Integration with Backend

The backend server now:
- ✅ Starts Qdrant before starting (via `start_backend_with_qdrant.sh`)
- ✅ Gracefully handles Qdrant connection failures
- ✅ Uses Qdrant for all vector database operations
- ✅ Supports all AI agents with vector database functionality

---

## Notes

- Qdrant data is persisted in `./qdrant_storage` directory
- The container will auto-restart on system reboot if Docker is configured for that
- If Docker is not running, the startup script will prompt you to start Docker Desktop
