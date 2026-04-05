#!/usr/bin/env bash
# Update CloudFront distribution E2I8B0C6RDAOGT origins to the current EC2 public DNS.
# Run after EC2 stop/start (public IP/DNS changes). Uses EC2 instance ID or tag to get current DNS.
#
# CloudFront viewers always use HTTPS on 443 (or HTTP 80) to the edge. For MCP streamable HTTP,
# this distribution uses a second origin (default id: cspulse-mcp-origin) with HTTP port 8001 so
# paths like /mcp* reach the MCP process directly. Ensure the EC2 security group allows inbound
# TCP 8001 from the internet (or tighten to CloudFront / your IP range).
#
# Usage:
#   ./scripts/update-cloudfront-origin.sh [EC2_INSTANCE_ID]
#   CSPULSE_EC2_INSTANCE_ID=i-xxxxx ./scripts/update-cloudfront-origin.sh
# Or set ORIGIN_HOST directly:
#   ORIGIN_HOST=ec2-54-89-43-246.compute-1.amazonaws.com ./scripts/update-cloudfront-origin.sh
#
# Optional:
#   CSPULSE_CLOUDFRONT_ID   (default E2I8B0C6RDAOGT)
#   CSPULSE_MCP_ORIGIN_ID   (default cspulse-mcp-origin) — origin whose HTTP port is set below
#   MCP_ORIGIN_HTTP_PORT    (default 8001) — set to 80 to proxy MCP via nginx only

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
DIST_ID="${CSPULSE_CLOUDFRONT_ID:-E2I8B0C6RDAOGT}"
MCP_ORIGIN_ID="${CSPULSE_MCP_ORIGIN_ID:-cspulse-mcp-origin}"
MCP_ORIGIN_HTTP_PORT="${MCP_ORIGIN_HTTP_PORT:-8001}"

# Resolve origin host: explicit ORIGIN_HOST, or from instance ID
ORIGIN_HOST="${ORIGIN_HOST}"
if [[ -z "$ORIGIN_HOST" ]]; then
  INSTANCE_ID="${1:-${CSPULSE_EC2_INSTANCE_ID}}"
  if [[ -z "$INSTANCE_ID" ]]; then
    INSTANCE_ID=$(aws ec2 describe-instances \
      --filters "Name=tag:Name,Values=cspulse-v6" "Name=instance-state-name,Values=running,pending" \
      --query 'Reservations[*].Instances[*].InstanceId' --output text --region "$AWS_REGION" 2>/dev/null | head -1)
  fi
  if [[ -z "$INSTANCE_ID" ]]; then
    echo "Usage: $0 [EC2_INSTANCE_ID]"
    echo "   or: ORIGIN_HOST=ec2-xx-xx-xx-xx.compute-1.amazonaws.com $0"
    echo "   or: CSPULSE_EC2_INSTANCE_ID=i-xxxxx $0"
    exit 1
  fi
  ORIGIN_HOST=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
    --query 'Reservations[0].Instances[0].PublicDnsName' --output text)
  if [[ -z "$ORIGIN_HOST" ]] || [[ "$ORIGIN_HOST" == "None" ]]; then
    echo "Could not get public DNS for instance $INSTANCE_ID. Is it running?"
    exit 1
  fi
fi

echo "Updating CloudFront distribution $DIST_ID origins to: $ORIGIN_HOST"
echo "  MCP origin id: $MCP_ORIGIN_ID → HTTP port $MCP_ORIGIN_HTTP_PORT (paths /mcp* use this origin)"

aws cloudfront get-distribution-config --id "$DIST_ID" --output json > /tmp/cf-get.json
ETAG=$(jq -r '.ETag' /tmp/cf-get.json)
jq --arg domain "$ORIGIN_HOST" --arg mcp_id "$MCP_ORIGIN_ID" --argjson mcp_port "$MCP_ORIGIN_HTTP_PORT" '
  .DistributionConfig
  | .Origins.Items |= map(
      .DomainName = $domain
      | if .Id == $mcp_id then .CustomOriginConfig |= (.HTTPPort = $mcp_port) else . end
    )
' /tmp/cf-get.json > /tmp/cf-distconfig.json
aws cloudfront update-distribution --id "$DIST_ID" --if-match "$ETAG" --distribution-config file:///tmp/cf-distconfig.json --output text
rm -f /tmp/cf-get.json /tmp/cf-distconfig.json

echo "Done. Distribution is updating (5–15 min)."
echo "  App (HTTPS): https://d2oqfugrb2ltg9.cloudfront.net/"
echo "  MCP (HTTPS, edge :443 → origin :${MCP_ORIGIN_HTTP_PORT}): https://d2oqfugrb2ltg9.cloudfront.net/mcp"
