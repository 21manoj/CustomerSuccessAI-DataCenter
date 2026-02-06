#!/bin/bash
# Setup script for Qdrant Cloud configuration

echo "🔧 Setting up Qdrant Cloud configuration..."
echo ""

# Qdrant Cloud credentials
QDRANT_URL="https://7528cec3-24f4-4584-bee2-ca371726134a.us-east-1-1.aws.cloud.qdrant.io"
QDRANT_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8t-hHzNql_9C-BEBs2Pye0l942C6HbBvz7Ro_DDKEH4"

# Check if .env file exists
if [ -f .env ]; then
    echo "📝 Updating existing .env file..."
    
    # Remove old Qdrant settings if they exist
    sed -i.bak '/^QDRANT_URL=/d' .env
    sed -i.bak '/^QDRANT_HOST=/d' .env
    sed -i.bak '/^QDRANT_PORT=/d' .env
    sed -i.bak '/^QDRANT_API_KEY=/d' .env
    
    # Add new Qdrant Cloud settings
    echo "" >> .env
    echo "# Qdrant Cloud Configuration" >> .env
    echo "QDRANT_URL=$QDRANT_URL" >> .env
    echo "QDRANT_API_KEY=$QDRANT_API_KEY" >> .env
else
    echo "📝 Creating new .env file..."
    cat > .env << EOF
# Qdrant Cloud Configuration
QDRANT_URL=$QDRANT_URL
QDRANT_API_KEY=$QDRANT_API_KEY
EOF
fi

echo ""
echo "✅ Qdrant Cloud configuration added to .env file"
echo ""
echo "Configuration:"
echo "  QDRANT_URL: $QDRANT_URL"
echo "  QDRANT_API_KEY: [configured]"
echo ""
echo "⚠️  Note: Restart the backend server for changes to take effect"
echo ""
