#!/usr/bin/env bash
# Amazon Linux 2023 Docker ships buildx 0.12; compose v5 requires >= 0.17.
# Installs a newer buildx binary to /usr/local/lib/docker/cli-plugins (run on EC2).
set -e

BUILDX_MIN_MINOR=17
BUILDX_INSTALL_VER="${CSPULSE_BUILDX_VERSION:-v0.34.0}"
PLUGIN_DIR="/usr/local/lib/docker/cli-plugins"

version_minor() {
  sudo docker buildx version 2>/dev/null | awk '{print $2}' | cut -d. -f2
}

minor="$(version_minor || echo 0)"
if [[ "${minor:-0}" -ge "$BUILDX_MIN_MINOR" ]]; then
  echo "docker buildx OK ($(sudo docker buildx version | head -1))"
  exit 0
fi

echo "Upgrading docker buildx (current minor=${minor}, need >=${BUILDX_MIN_MINOR})..."
sudo mkdir -p "$PLUGIN_DIR"
curl -fsSL \
  "https://github.com/docker/buildx/releases/download/${BUILDX_INSTALL_VER}/buildx-${BUILDX_INSTALL_VER}.linux-amd64" \
  -o /tmp/docker-buildx-new
sudo install -m 0755 /tmp/docker-buildx-new "$PLUGIN_DIR/docker-buildx"
rm -f /tmp/docker-buildx-new
sudo docker buildx version
