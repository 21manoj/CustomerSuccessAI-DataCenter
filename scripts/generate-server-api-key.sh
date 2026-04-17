#!/usr/bin/env bash
# Generate a server-level MCP API key and update ~/cspulse/.env
#
# Usage:
#   ./scripts/generate-server-api-key.sh              # Local — updates .env
#   ssh ec2-user@<host> 'bash -s' < scripts/generate-server-api-key.sh  # Remote
#
# The server key bypasses per-customer scoping — use for:
#   - Internal CS Pulse team (access all customers)
#   - Demo MCP connectors in Claude.ai
#   - Load driver with --api-key flag
#
# After generating, restart the cs-pulse container to pick up the new key.

set -e

KEY="csp_server_$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 40)"

# Find .env file
ENV_FILE="${CSPULSE_ENV:-${HOME}/cspulse/.env}"
if [[ ! -f "$ENV_FILE" ]]; then
    ENV_FILE=".env"
fi

if [[ -f "$ENV_FILE" ]]; then
    # Update or add MCP_SERVER_API_KEY
    if grep -q '^MCP_SERVER_API_KEY=' "$ENV_FILE"; then
        OLD_KEY=$(grep '^MCP_SERVER_API_KEY=' "$ENV_FILE" | cut -d= -f2)
        sed -i.bak "s|^MCP_SERVER_API_KEY=.*|MCP_SERVER_API_KEY=${KEY}|" "$ENV_FILE"
        echo "Updated MCP_SERVER_API_KEY in $ENV_FILE"
        echo "  Old key: ${OLD_KEY:0:16}..."
    else
        echo "MCP_SERVER_API_KEY=${KEY}" >> "$ENV_FILE"
        echo "Added MCP_SERVER_API_KEY to $ENV_FILE"
    fi
else
    echo "No .env file found at $ENV_FILE"
    echo "Set CSPULSE_ENV to your .env path, or run from the cspulse directory."
    echo ""
fi

echo ""
echo "Server API Key: $KEY"
echo ""
echo "Use as:"
echo "  Authorization: Bearer $KEY"
echo ""
echo "Next steps:"
echo "  1. Restart cs-pulse container: cd ~/cspulse && sudo docker compose -f docker-compose.ec2-registry.yml up -d --force-recreate cs-pulse"
echo "  2. Update Claude.ai MCP connector with this key"
echo "  3. Test: curl -s -H 'Authorization: Bearer $KEY' https://<host>/mcp"
