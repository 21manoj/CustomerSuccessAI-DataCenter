#!/usr/bin/env bash
# Deploy CS Pulse on EC2 by git pull + native amd64 docker build (no ECR).
# Faster than Mac buildx → push → rehydrate for day-to-day iteration.
#
# Prereq (one-time): ~/cspulse/.env on EC2 with secrets (from registry deploy).
# Auth for private GitHub (pick one):
#   - export CSPULSE_GITHUB_TOKEN=<PAT with repo read>  (HTTPS clone/pull)
#   - or one-time: ssh to EC2 and git clone git@github.com:21manoj/CustomerSuccessAI-DataCenter.git
#
# Usage (from laptop, repo root):
#   CSPULSE_SSH_KEY_FILE=~/.ssh/cspulse-v6-key.pem \
#   CSPULSE_EC2_INSTANCE_ID=i-019ab6efa55514eb1 \
#   ./scripts/deploy-ec2-git-pull.sh
#
#   ./scripts/deploy-ec2-git-pull.sh --no-cache
#   ./scripts/deploy-ec2-git-pull.sh --branch main
#
# See: docs/DEPLOYMENT_PATTERN_REGISTRY.md § EC2 git pull + build

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${CSPULSE_SSH_KEY_FILE:-${REPO_ROOT}/cspulse-v6-key.pem}"
AWS_REGION="${AWS_REGION:-us-east-1}"
INSTANCE_ID="${CSPULSE_EC2_INSTANCE_ID:-}"
BRANCH="${CSPULSE_GIT_BRANCH:-main}"
NO_CACHE=""
GIT_REMOTE="${CSPULSE_GIT_REMOTE:-https://github.com/21manoj/CustomerSuccessAI-DataCenter.git}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-cache) NO_CACHE="--no-cache" ;;
    --branch) BRANCH="${2:?--branch requires a name}"; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
  shift
done

if [[ -z "$INSTANCE_ID" ]]; then
  INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cspulse-v6" "Name=instance-state-name,Values=pending,running,stopped" \
    --query 'Reservations[*].Instances[*].InstanceId' --output text --region "$AWS_REGION" 2>/dev/null | head -1)
fi
if [[ -z "$INSTANCE_ID" ]]; then
  echo "Set CSPULSE_EC2_INSTANCE_ID or pass a running cspulse-v6 instance."
  exit 1
fi
if [[ ! -f "$KEY_FILE" ]]; then
  echo "SSH key not found: $KEY_FILE"
  exit 1
fi

STATE=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
  --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || true)
if [[ "$STATE" == "stopped" ]]; then
  echo "Starting instance $INSTANCE_ID..."
  aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --output text
  aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$AWS_REGION"
elif [[ "$STATE" != "running" ]] && [[ "$STATE" != "pending" ]]; then
  echo "Instance not runnable (state: $STATE)"
  exit 1
fi

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
if [[ -z "$PUBLIC_IP" ]] || [[ "$PUBLIC_IP" == "None" ]]; then
  echo "No public IP for $INSTANCE_ID"
  exit 1
fi

echo "=== EC2 git pull + build ==="
echo "  Instance: $INSTANCE_ID"
echo "  Host:     $PUBLIC_IP"
echo "  Branch:   $BRANCH"
echo ""

SSH=(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}")

# Pass token only if set locally (not echoed in this script's args)
TOKEN_ENV=""
if [[ -n "${CSPULSE_GITHUB_TOKEN:-}" ]]; then
  TOKEN_ENV="CSPULSE_GITHUB_TOKEN=$(printf '%q' "$CSPULSE_GITHUB_TOKEN")"
fi

"${SSH[@]}" "set -e
  ${TOKEN_ENV}
  export CSPULSE_REPO_DIR=\"\${CSPULSE_REPO_DIR:-\$HOME/CustomerSuccessAI-DataCenter}\"
  export CSPULSE_GIT_BRANCH='${BRANCH}'
  export CSPULSE_GIT_REMOTE='${GIT_REMOTE}'

  if ! command -v git >/dev/null 2>&1; then
    echo 'Installing git...'
    sudo dnf install -y git
  fi

  REPO=\"\$CSPULSE_REPO_DIR\"
  if [[ ! -d \"\$REPO/.git\" ]]; then
    echo \"Cloning into \$REPO ...\"
    if [[ -n \"\${CSPULSE_GITHUB_TOKEN:-}\" ]]; then
      CLONE_URL=\"\${CSPULSE_GIT_REMOTE/https:\\/\\//https://\${CSPULSE_GITHUB_TOKEN}@}\"
      git clone --branch '${BRANCH}' \"\$CLONE_URL\" \"\$REPO\"
    else
      echo 'No git repo on EC2. Either:'
      echo '  export CSPULSE_GITHUB_TOKEN=<read-only PAT> and re-run, or'
      echo '  ssh in and: git clone git@github.com:21manoj/CustomerSuccessAI-DataCenter.git \$REPO'
      exit 1
    fi
  else
    cd \"\$REPO\"
    git fetch origin
    git checkout '${BRANCH}'
    if [[ -n \"\${CSPULSE_GITHUB_TOKEN:-}\" ]] && [[ \"\$(git remote get-url origin 2>/dev/null)\" == https://github.com/* ]]; then
      git remote set-url origin \"\${CSPULSE_GIT_REMOTE/https:\\/\\//https://\${CSPULSE_GITHUB_TOKEN}@}\"
    fi
    git pull --ff-only origin '${BRANCH}'
  fi

  # Reuse secrets from ECR deploy layout
  if [[ -f \"\$HOME/cspulse/.env\" ]] && [[ ! -f \"\$REPO/kpi-dashboard/.env\" ]]; then
    cp \"\$HOME/cspulse/.env\" \"\$REPO/kpi-dashboard/.env\"
    echo 'Copied ~/cspulse/.env → kpi-dashboard/.env'
  fi
  if [[ -f \"\$REPO/kpi-dashboard/.env\" ]] && ! grep -q '^SESSION_COOKIE_SECURE=' \"\$REPO/kpi-dashboard/.env\" 2>/dev/null; then
    echo 'SESSION_COOKIE_SECURE=false' >> \"\$REPO/kpi-dashboard/.env\"
  fi

  # Stop registry-based stack (keep volumes); build compose uses the same project name.
  if [[ -f \"\$HOME/cspulse/docker-compose.ec2-registry.yml\" ]]; then
    echo 'Stopping ECR/registry stack (volumes kept)...'
    cd \"\$HOME/cspulse\"
    sudo docker compose -p cspulse \
      -f docker-compose.ec2-registry.yml \
      -f docker-compose.ec2-loaddriver.yml \
      -f docker-compose.ec2-platform-replica.yml \
      down 2>/dev/null || true
  fi

  cd \"\$REPO\"
  chmod +x scripts/ec2-git-pull-rebuild.sh
  ./scripts/ec2-git-pull-rebuild.sh ${NO_CACHE}
"

echo ""
echo "Waiting for /api/health..."
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf --max-time 5 "http://${PUBLIC_IP}/api/health" >/dev/null; then
    echo "Health OK (attempt $i)"
    echo ""
    echo "=== Deploy complete ==="
    echo "  App:    http://${PUBLIC_IP}/"
    echo "  Health: curl -s http://${PUBLIC_IP}/api/health"
    echo "  SSH:    ssh -i $KEY_FILE ec2-user@${PUBLIC_IP}"
    exit 0
  fi
  sleep 10
done
echo "WARN: health check did not pass in ~100s — check: ssh -i $KEY_FILE ec2-user@${PUBLIC_IP} sudo docker compose -p cspulse -f ~/CustomerSuccessAI-DataCenter/kpi-dashboard/docker-compose.ec2-build.yml ps"
exit 1
