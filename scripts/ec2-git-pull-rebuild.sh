#!/usr/bin/env bash
# Run on the EC2 host (as ec2-user). Updates code from git and rebuilds containers.
#
# Prereq: one-time clone at CSPULSE_REPO_DIR (default ~/CustomerSuccessAI-DataCenter),
#         and kpi-dashboard/.env with POSTGRES_PASSWORD, SECRET_KEY, API keys.
#
# Usage:
#   ./scripts/ec2-git-pull-rebuild.sh           # pull + build (cached) + up -d
#   ./scripts/ec2-git-pull-rebuild.sh --no-cache
#
set -e
REPO_ROOT="${CSPULSE_REPO_DIR:-$HOME/CustomerSuccessAI-DataCenter}"
DASH="${REPO_ROOT}/kpi-dashboard"
# Use project name cspulse so volumes match an existing ECR/registry deploy (cspulse_pgdata, etc.).
COMPOSE=(sudo docker compose -p cspulse -f docker-compose.ec2-build.yml)

NO_CACHE=()
if [[ "${1:-}" == "--no-cache" ]]; then
  NO_CACHE=(--no-cache)
fi

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "Expected git repo at: $REPO_ROOT"
  echo "Clone with: git clone <your-remote> $REPO_ROOT"
  exit 1
fi

cd "$REPO_ROOT"
git pull

cd "$DASH"
"${COMPOSE[@]}" build "${NO_CACHE[@]}"
"${COMPOSE[@]}" up -d
"${COMPOSE[@]}" ps
