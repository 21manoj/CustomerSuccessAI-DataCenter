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

# Sanity check — the compose file in the same directory as .env must
# pass MCP_SERVER_API_KEY through to the cs-pulse container, otherwise
# the server has no value to compare against and rejects the key as
# "expired" (see auth.py validate_server_key()).
COMPOSE_DIR="$(dirname "$ENV_FILE")"
COMPOSE_HIT=""
for cf in "$COMPOSE_DIR"/docker-compose*.yml; do
    [[ -f "$cf" ]] || continue
    if grep -q "MCP_SERVER_API_KEY:" "$cf" 2>/dev/null; then
        COMPOSE_HIT="$cf"
        break
    fi
done

if [[ -z "$COMPOSE_HIT" ]]; then
    echo "⚠️  WARNING: no docker-compose*.yml in $COMPOSE_DIR passes MCP_SERVER_API_KEY to the container."
    echo "    The container will not see this key and will reject it as 'expired' on every request."
    echo "    Add this line under the cs-pulse 'environment:' block:"
    echo "        MCP_SERVER_API_KEY: \${MCP_SERVER_API_KEY}"
    echo ""
fi

echo "Use as:"
echo "  Authorization: Bearer $KEY"
echo "  — or —"
echo "  https://<host>/mcp?api_key=$KEY    (URL form, demo only — rotates after demos)"
echo ""
echo "Next steps:"
echo "  1. Restart cs-pulse container: cd ~/cspulse && sudo docker compose -f docker-compose.ec2-registry.yml up -d --force-recreate cs-pulse"
echo "  2. Verify env reached the container: sudo docker exec cspulse-platform env | grep MCP_SERVER_API_KEY"
echo "  3. Update Claude.ai MCP connector with this key"
echo "  4. Test: curl -s -H 'Authorization: Bearer $KEY' https://<host>/mcp"
