#!/usr/bin/env bash
# Update CloudFront distribution E2I8B0C6RDAOGT origins to the current EC2 public DNS.
# Run after EC2 stop/start (public IP/DNS changes). Uses EC2 instance ID or tag to get current DNS.
#
# Usage:
#   ./scripts/update-cloudfront-origin.sh [EC2_INSTANCE_ID]
#   CSPULSE_EC2_INSTANCE_ID=i-xxxxx ./scripts/update-cloudfront-origin.sh
# Or set ORIGIN_HOST directly:
#   ORIGIN_HOST=ec2-54-89-43-246.compute-1.amazonaws.com ./scripts/update-cloudfront-origin.sh

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
DIST_ID="${CSPULSE_CLOUDFRONT_ID:-E2I8B0C6RDAOGT}"

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

aws cloudfront get-distribution-config --id "$DIST_ID" --output json > /tmp/cf-get.json
ETAG=$(jq -r '.ETag' /tmp/cf-get.json)
jq --arg domain "$ORIGIN_HOST" '.DistributionConfig | .Origins.Items |= (map(.DomainName = $domain))' /tmp/cf-get.json > /tmp/cf-distconfig.json
aws cloudfront update-distribution --id "$DIST_ID" --if-match "$ETAG" --distribution-config file:///tmp/cf-distconfig.json --output text
rm -f /tmp/cf-get.json /tmp/cf-distconfig.json

echo "Done. Distribution is updating (5–15 min). HTTPS: https://d2oqfugrb2ltg9.cloudfront.net"
