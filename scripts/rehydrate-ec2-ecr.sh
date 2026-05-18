#!/usr/bin/env bash
# Rehydrate EC2: start instance (if stopped), pull all images from ECR, run platform + postgres + load-driver.
# Uses ECR only (no S3). Requires: AWS CLI, SSH key (cspulse-v6-key.pem), instance role with ECR read.
#
# For faster day-to-day deploys (no Mac buildx / ECR push), prefer:
#   ./scripts/deploy-ec2-git-pull.sh
#
# Usage:
#   ./scripts/rehydrate-ec2-ecr.sh [INSTANCE_ID]
#   CSPULSE_EC2_INSTANCE_ID=i-xxxxx ./scripts/rehydrate-ec2-ecr.sh
#
# If INSTANCE_ID is omitted, uses CSPULSE_EC2_INSTANCE_ID or discovers one by tag Name=cspulse-v6.

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${CSPULSE_SSH_KEY_FILE:-${REPO_ROOT}/cspulse-v6-key.pem}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DEFAULT_ECR_REGISTRY="822824391150.dkr.ecr.us-east-1.amazonaws.com"

INSTANCE_ID="${1:-${CSPULSE_EC2_INSTANCE_ID}}"
if [[ -z "$INSTANCE_ID" ]]; then
  INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cspulse-v6" "Name=instance-state-name,Values=pending,running,stopped" \
    --query 'Reservations[*].Instances[*].InstanceId' --output text --region "$AWS_REGION" 2>/dev/null | head -1)
fi
if [[ -z "$INSTANCE_ID" ]]; then
  echo "Usage: $0 <INSTANCE_ID>"
  echo "   or: CSPULSE_EC2_INSTANCE_ID=i-xxxxx $0"
  echo "No instance found with tag Name=cspulse-v6. Set CSPULSE_EC2_INSTANCE_ID or pass instance ID."
  exit 1
fi

if [[ ! -f "$KEY_FILE" ]]; then
  echo "SSH key not found: $KEY_FILE"
  exit 1
fi

# Resolve ECR registry from local .env or default
REGISTRY="$DEFAULT_ECR_REGISTRY"
for env_candidate in "${REPO_ROOT}/kpi-dashboard/.env" "${REPO_ROOT}/kpi-dashboard/backend/.env"; do
  if [[ -f "$env_candidate" ]]; then
    val=$(grep -E '^REGISTRY=' "$env_candidate" 2>/dev/null | head -1 | sed 's/^REGISTRY=//' | tr -d '\r')
    if [[ -n "$val" ]]; then REGISTRY="$val"; break; fi
  fi
done

echo "=== Rehydrate EC2 from ECR ==="
echo "  Instance:   $INSTANCE_ID"
echo "  Region:     $AWS_REGION"
echo "  Registry:   $REGISTRY"
echo ""

# 1) Start instance if stopped
STATE=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
  --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || true)
if [[ "$STATE" == "stopped" ]]; then
  echo "Starting instance..."
  aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --output text
  echo "Waiting for instance to be running..."
  aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$AWS_REGION"
  echo "Instance is running."
elif [[ "$STATE" != "running" ]] && [[ "$STATE" != "pending" ]]; then
  echo "Instance is not runnable (state: $STATE). Start it from the console or use: aws ec2 start-instances --instance-ids $INSTANCE_ID"
  exit 1
fi

# 2) Get public IP and DNS
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
PUBLIC_DNS=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
  --query 'Reservations[0].Instances[0].PublicDnsName' --output text)

if [[ -z "$PUBLIC_IP" ]] || [[ "$PUBLIC_IP" == "None" ]]; then
  echo "No public IP for instance. Check VPC/subnet and try again."
  exit 1
fi

echo "  Public IP:  $PUBLIC_IP"
echo "  Public DNS: $PUBLIC_DNS"
echo ""

# 3) Copy compose files to ~/cspulse
echo "Copying compose files to EC2 ~/cspulse..."
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" \
  "${REPO_ROOT}/kpi-dashboard/docker-compose.ec2-registry.yml" \
  "ec2-user@${PUBLIC_IP}:~/cspulse/docker-compose.ec2-registry.yml"
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" \
  "${REPO_ROOT}/docker-compose.ec2-loaddriver.yml" \
  "ec2-user@${PUBLIC_IP}:~/cspulse/docker-compose.ec2-loaddriver.yml"
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" \
  "${REPO_ROOT}/kpi-dashboard/docker-compose.ec2-platform-replica.yml" \
  "ec2-user@${PUBLIC_IP}:~/cspulse/docker-compose.ec2-platform-replica.yml"
echo "Compose files copied."
echo ""

# 4) ECR login from local (instance role may not have ECR; your AWS CLI does), then on EC2: pull, up -d
echo "Getting ECR token and logging in on EC2..."
ECR_TOKEN_FILE=$(mktemp)
trap 'rm -f "$ECR_TOKEN_FILE"' EXIT
aws ecr get-login-password --region "$AWS_REGION" > "$ECR_TOKEN_FILE"
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" "$ECR_TOKEN_FILE" "ec2-user@${PUBLIC_IP}:~/cspulse/.ecr-token"
echo "On EC2: ensuring REGISTRY in .env, docker login, pull, and starting all services..."
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" "set -e
  cd ~/cspulse
  test -f .env || cp .env.example .env 2>/dev/null || true
  if ! grep -q '^REGISTRY=' .env 2>/dev/null; then
    echo 'REGISTRY=${REGISTRY}' >> .env
  fi
  # Session cookie Secure flag — for direct-IP HTTP demo access, the platform
  # container must NOT mark the cookie as Secure (browsers drop Secure cookies
  # over HTTP, breaking login). CloudFront still terminates HTTPS at the edge
  # for visitors using the d2oqfugrb2ltg9.cloudfront.net URL, so end-to-end
  # secure access remains possible via CloudFront.
  if ! grep -q '^SESSION_COOKIE_SECURE=' .env 2>/dev/null; then
    echo 'SESSION_COOKIE_SECURE=false' >> .env
  fi
  sudo docker login --username AWS --password-stdin ${REGISTRY} < .ecr-token && rm -f .ecr-token
  sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml -f docker-compose.ec2-platform-replica.yml pull
  sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml -f docker-compose.ec2-platform-replica.yml up -d
  sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml -f docker-compose.ec2-platform-replica.yml ps
"

# Update CloudFront origins to this EC2 so HTTPS works (optional; skip if script missing or env set)
if [[ -z "${SKIP_CLOUDFRONT_UPDATE:-}" ]] && [[ -x "${REPO_ROOT}/scripts/update-cloudfront-origin.sh" ]]; then
  echo "Updating CloudFront origins to current EC2 DNS..."
  ORIGIN_HOST="$PUBLIC_DNS" "${REPO_ROOT}/scripts/update-cloudfront-origin.sh" 2>/dev/null || true
fi

echo ""
echo "=== Rehydration complete ==="
echo "  App URL:    http://${PUBLIC_IP}/"
echo "  Platform B (load-test / extra capacity): http://${PUBLIC_IP}:9080/  (same DB)"
echo "  Health B:   curl -s http://${PUBLIC_IP}:9080/api/health"
echo "  Health:     curl -s http://${PUBLIC_IP}/api/health"
echo "  HTTPS:      https://d2oqfugrb2ltg9.cloudfront.net/ (CloudFront; may take 5–15 min to deploy)"
echo "  MCP (HTTPS): https://d2oqfugrb2ltg9.cloudfront.net/mcp"
echo "  SSH:        ssh -i $KEY_FILE ec2-user@${PUBLIC_IP}"
echo ""
