# 🐳 KPI Dashboard Docker Setup

This guide explains how to build and run the KPI Dashboard using Docker containers.

## 📋 Prerequisites

- Docker Desktop installed and running
- Docker Compose v3.8+
- At least 4GB RAM available for containers

## 🚀 Quick Start

### 1. Build and Start Services

```bash
# Make scripts executable
chmod +x build-docker.sh docker-commands.sh

# Build and start all services
./build-docker.sh
```

### 2. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5059
- **API Documentation**: http://localhost:5059/api/

### 3. Check Service Status

```bash
# Check if services are running
./docker-commands.sh status

# Test service health
./docker-commands.sh test
```

## 🛠️ Docker Commands

Use the `docker-commands.sh` script for easy management:

```bash
# Build containers
./docker-commands.sh build

# Start services
./docker-commands.sh start

# Stop services
./docker-commands.sh stop

# Restart services
./docker-commands.sh restart

# View logs
./docker-commands.sh logs

# Check status
./docker-commands.sh status

# Clean up
./docker-commands.sh clean

# Open backend shell
./docker-commands.sh shell-backend

# Open frontend shell
./docker-commands.sh shell-frontend

# Test services
./docker-commands.sh test
```

## 📁 Project Structure

```
kpi-dashboard/
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── ... (backend files)
├── src/
│   └── ... (frontend files)
├── Dockerfile (frontend)
├── docker-compose.yml
├── docker.env
├── build-docker.sh
└── docker-commands.sh
```

## 🔧 Configuration

### Environment Variables

The Docker setup uses the `docker.env` file for configuration. Key variables:

- `FLASK_APP=app.py`
- `FLASK_ENV=production`
- `OPENAI_API_KEY=your-api-key`
- `SQLALCHEMY_DATABASE_URI=sqlite:///kpi_dashboard.db`

### Volumes

The following directories are mounted for data persistence:

- `./backend/instance` - Database files
- `./backend/uploads` - Uploaded files
- `./backend/qdrant_storage` - Vector database storage

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts**: Make sure ports 3000 and 5059 are available
2. **Permission issues**: Ensure Docker has access to the project directory
3. **Memory issues**: Allocate at least 4GB RAM to Docker Desktop

### Debug Commands

```bash
# View detailed logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Check container status
docker-compose ps

# Access container shell
docker-compose exec backend /bin/bash
docker-compose exec frontend /bin/sh

# Restart specific service
docker-compose restart backend
docker-compose restart frontend
```

### Reset Everything

```bash
# Stop and remove all containers, networks, and volumes
docker-compose down -v
docker system prune -f

# Rebuild from scratch
./build-docker.sh
```

## 📊 Monitoring

### Health Checks

Both services have health checks configured:

- **Backend**: Checks `http://localhost:5059/` every 30s
- **Frontend**: Checks `http://localhost:3000/` every 30s

### Logs

View logs in real-time:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

## 🚀 Production Considerations

For production deployment, consider:

1. **Environment Variables**: Use proper secrets management
2. **Database**: Use external database (PostgreSQL, MySQL)
3. **Reverse Proxy**: Use nginx or similar
4. **SSL/TLS**: Configure HTTPS
5. **Monitoring**: Add monitoring and logging
6. **Scaling**: Use Docker Swarm or Kubernetes

## 📝 Next Steps

1. Test the Docker setup locally
2. Verify all features work correctly
3. Plan cloud deployment strategy
4. Set up CI/CD pipeline
5. Configure production environment

## 🤝 Support

If you encounter issues:

1. Check the logs: `./docker-commands.sh logs`
2. Verify service status: `./docker-commands.sh status`
3. Test connectivity: `./docker-commands.sh test`
4. Clean and rebuild: `./docker-commands.sh clean && ./build-docker.sh`
