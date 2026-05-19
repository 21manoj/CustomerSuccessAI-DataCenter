#!/usr/bin/env bash
# Run on the EC2 host (as ec2-user). Rebuilds containers from a git clone (native amd64).
# Usually invoked via ./scripts/deploy-ec2-git-pull.sh from your laptop.
#
# Prereq: clone at CSPULSE_REPO_DIR (default ~/CustomerSuccessAI-DataCenter),
#         kpi-dashboard/.env with POSTGRES_PASSWORD, SECRET_KEY, API keys.
#
# Usage:
#   ./scripts/ec2-git-pull-rebuild.sh           # build (cached) + up -d
#   ./scripts/ec2-git-pull-rebuild.sh --no-cache
#
set -e
REPO_ROOT="${CSPULSE_REPO_DIR:-$HOME/CustomerSuccessAI-DataCenter}"
DASH="${REPO_ROOT}/kpi-dashboard"
BRANCH="${CSPULSE_GIT_BRANCH:-main}"
# Use project name cspulse so volumes match an existing ECR/registry deploy (cspulse_pgdata, etc.).
COMPOSE=(sudo docker compose -p cspulse -f docker-compose.ec2-build.yml)

NO_CACHE=()
if [[ "${1:-}" == "--no-cache" ]]; then
  NO_CACHE=(--no-cache)
fi

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "Expected git repo at: $REPO_ROOT"
  echo "From laptop: ./scripts/deploy-ec2-git-pull.sh (bootstraps clone + build)"
  exit 1
fi

if [[ ! -f "$DASH/.env" ]]; then
  echo "Missing $DASH/.env — copy from ~/cspulse/.env or scp from laptop."
  exit 1
fi

cd "$REPO_ROOT"
git fetch origin
git checkout "$BRANCH"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

cd "$DASH"
"${REPO_ROOT}/scripts/ensure-ec2-docker-buildx.sh"
echo "Building on EC2 ($(uname -m))..."
"${COMPOSE[@]}" build "${NO_CACHE[@]}"
"${COMPOSE[@]}" up -d
"${COMPOSE[@]}" ps
curl -sf http://localhost/api/health && echo " — health OK" || echo "WARN: /api/health not ready yet"
