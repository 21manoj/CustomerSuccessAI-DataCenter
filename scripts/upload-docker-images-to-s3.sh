#!/usr/bin/env bash
# Save the three CS Pulse Docker images to tarballs and upload to S3.
#
# Prerequisites:
#   - Docker images built (run ./scripts/build-and-validate-docker.sh or build manually)
#   - AWS CLI installed and configured (aws configure)
#   - S3 bucket created (e.g. ./scripts/aws-s3-container-bucket.sh [bucket-name])
#
# Usage:
#   ./scripts/upload-docker-images-to-s3.sh <bucket-name> [region]
#   Or: CSPULSE_S3_BUCKET=my-bucket ./scripts/upload-docker-images-to-s3.sh
#
# Images uploaded:
#   - containers/cspulse-platform.tar.gz   (from kpi-dashboard-cs-pulse:latest)
#   - containers/cspulse-postgres.tar.gz   (from kpi-dashboard-postgres:latest)
#   - containers/cspulse-load-driver.tar.gz (from cspulse-load-driver:latest)

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUCKET_NAME="${CSPULSE_S3_BUCKET:-$1}"
AWS_REGION="${2:-us-east-1}"
S3_PREFIX="containers"

if [[ -z "$BUCKET_NAME" ]]; then
  echo "Usage: $0 <bucket-name> [region]"
  echo "   Or: CSPULSE_S3_BUCKET=my-bucket $0"
  echo ""
  echo "Create a bucket first: ./scripts/aws-s3-container-bucket.sh my-bucket us-east-1"
  exit 1
fi

echo "=== Uploading Docker images to S3 ==="
echo "  Bucket: s3://${BUCKET_NAME}/${S3_PREFIX}/"
echo "  Region: ${AWS_REGION}"
echo ""

# Check images exist
for img in kpi-dashboard-cs-pulse:latest kpi-dashboard-postgres:latest cspulse-load-driver:latest; do
  if ! docker image inspect "$img" &>/dev/null; then
    echo "ERROR: Image $img not found. Build first: ./scripts/build-and-validate-docker.sh"
    exit 1
  fi
done

WORKDIR="${TMPDIR:-/tmp}/cspulse-s3-upload-$$"
mkdir -p "$WORKDIR"
trap "rm -rf '$WORKDIR'" EXIT

echo "=== 1. Saving Docker images to tarballs (gzip) ==="
docker save kpi-dashboard-cs-pulse:latest | gzip -9 > "$WORKDIR/cspulse-platform.tar.gz"
echo "  Saved cspulse-platform.tar.gz ($(du -h "$WORKDIR/cspulse-platform.tar.gz" | cut -f1))"

docker save kpi-dashboard-postgres:latest | gzip -9 > "$WORKDIR/cspulse-postgres.tar.gz"
echo "  Saved cspulse-postgres.tar.gz ($(du -h "$WORKDIR/cspulse-postgres.tar.gz" | cut -f1))"

docker save cspulse-load-driver:latest | gzip -9 > "$WORKDIR/cspulse-load-driver.tar.gz"
echo "  Saved cspulse-load-driver.tar.gz ($(du -h "$WORKDIR/cspulse-load-driver.tar.gz" | cut -f1))"

echo ""
echo "=== 2. Uploading to S3 ==="
aws s3 cp "$WORKDIR/cspulse-platform.tar.gz"   "s3://${BUCKET_NAME}/${S3_PREFIX}/" --region "$AWS_REGION"
aws s3 cp "$WORKDIR/cspulse-postgres.tar.gz"   "s3://${BUCKET_NAME}/${S3_PREFIX}/" --region "$AWS_REGION"
aws s3 cp "$WORKDIR/cspulse-load-driver.tar.gz" "s3://${BUCKET_NAME}/${S3_PREFIX}/" --region "$AWS_REGION"

echo ""
echo "Done. Images in s3://${BUCKET_NAME}/${S3_PREFIX}/:"
aws s3 ls "s3://${BUCKET_NAME}/${S3_PREFIX}/" --region "$AWS_REGION"
echo ""
echo "To load on EC2:"
echo "  aws s3 cp s3://${BUCKET_NAME}/${S3_PREFIX}/cspulse-platform.tar.gz . && gunzip -c cspulse-platform.tar.gz | docker load"
echo "  aws s3 cp s3://${BUCKET_NAME}/${S3_PREFIX}/cspulse-postgres.tar.gz . && gunzip -c cspulse-postgres.tar.gz | docker load"
echo "  aws s3 cp s3://${BUCKET_NAME}/${S3_PREFIX}/cspulse-load-driver.tar.gz . && gunzip -c cspulse-load-driver.tar.gz | docker load"
