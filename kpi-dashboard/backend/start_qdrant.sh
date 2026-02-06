#!/bin/bash
# DEPRECATED: Start Qdrant vector database server
# 
# WARNING: This script is deprecated. We are now using Qdrant Cloud.
# This script is kept for reference but should not be used in production.
# 
# To use Qdrant, set QDRANT_URL and QDRANT_API_KEY in your .env file.
# Example:
#   QDRANT_URL=https://your-cluster.qdrant.io
#   QDRANT_API_KEY=your-api-key

set -e

echo "⚠️  WARNING: This script is deprecated!"
echo "   We are now using Qdrant Cloud instead of local Qdrant server."
echo "   Please set QDRANT_URL and QDRANT_API_KEY in your .env file."
echo ""
echo "   Exiting without starting local Qdrant server..."
exit 0

# Original script code below (disabled):

QDRANT_CONTAINER_NAME="qdrant-server"
QDRANT_PORT=6333
QDRANT_GRPC_PORT=6334
QDRANT_STORAGE_PATH="./qdrant_storage"

echo "🔍 Starting Qdrant Vector Database..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker daemon is not running."
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

# Check if Qdrant container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
    echo "📦 Found existing Qdrant container"
    
    # Check if it's running
    if docker ps --format '{{.Names}}' | grep -q "^${QDRANT_CONTAINER_NAME}$"; then
        echo "✅ Qdrant is already running"
        exit 0
    else
        echo "🔄 Starting existing Qdrant container..."
        docker start ${QDRANT_CONTAINER_NAME}
    fi
else
    echo "🆕 Creating new Qdrant container..."
    # Create storage directory if it doesn't exist
    mkdir -p ${QDRANT_STORAGE_PATH}
    
    # Start Qdrant container
    docker run -d \
        --name ${QDRANT_CONTAINER_NAME} \
        -p ${QDRANT_PORT}:6333 \
        -p ${QDRANT_GRPC_PORT}:6334 \
        -v "$(pwd)/${QDRANT_STORAGE_PATH}:/qdrant/storage" \
        qdrant/qdrant:latest
fi

# Wait for Qdrant to be ready
echo "⏳ Waiting for Qdrant to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:${QDRANT_PORT}/health > /dev/null 2>&1; then
        echo "✅ Qdrant is ready and running on port ${QDRANT_PORT}"
        echo "   Health: http://localhost:${QDRANT_PORT}/health"
        echo "   Dashboard: http://localhost:${QDRANT_PORT}/dashboard"
        exit 0
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 1
done

echo "❌ Error: Qdrant failed to start after ${MAX_RETRIES} seconds"
exit 1
