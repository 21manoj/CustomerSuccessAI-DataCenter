#!/bin/bash
# Build and test Docker containers locally

echo "🐳 Building KPI Dashboard Docker containers..."

# Stop any running containers
echo "Stopping existing containers..."
docker-compose down

# Build the containers
echo "Building backend container..."
docker-compose build backend

echo "Building frontend container..."
docker-compose build frontend

# Copy environment file
echo "Setting up environment..."
cp docker.env backend/.env

# Start the services
echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Check service health
echo "Checking service health..."
echo "Backend health:"
curl -f http://localhost:5059/ || echo "Backend not ready yet"

echo "Frontend health:"
curl -f http://localhost:3000/ || echo "Frontend not ready yet"

echo "✅ Docker containers built and started!"
echo "Backend: http://localhost:5059"
echo "Frontend: http://localhost:3000"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
