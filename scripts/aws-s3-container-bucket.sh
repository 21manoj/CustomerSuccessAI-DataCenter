#!/usr/bin/env bash
# Create an S3 bucket for CS Pulse container artifacts (e.g. docker save tarballs).
# Plan for ~50 GB; S3 billing is pay-per-use (no reservation required).
#
# Prerequisites: AWS CLI installed and configured (aws configure).
# Usage: ./scripts/aws-s3-container-bucket.sh [bucket-name] [region]

set -e
BUCKET_NAME="${1:-cspulse-container-artifacts-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "CHANGE_ME")"
AWS_REGION="${2:-us-east-1}"

if [[ "$BUCKET_NAME" == *"CHANGE_ME"* ]]; then
  echo "Could not get AWS account ID. Pass bucket name as first argument, e.g.:"
  echo "  $0 my-cspulse-containers us-east-1"
  exit 1
fi

echo "Creating S3 bucket: s3://${BUCKET_NAME} (region: ${AWS_REGION})"
aws s3 mb "s3://${BUCKET_NAME}" --region "$AWS_REGION"

echo "Enabling versioning..."
aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled

echo "Ensuring public access is blocked..."
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo "Creating prefix for container tarballs (optional)..."
aws s3api put-object --bucket "$BUCKET_NAME" --key "containers/" --content-length 0 2>/dev/null || true

echo ""
echo "Done. Bucket ready for ~50 GB of container artifacts."
echo "  Bucket: s3://${BUCKET_NAME}"
echo "  Region: ${AWS_REGION}"
echo "  Upload example: aws s3 cp cspulse-platform.tar.gz s3://${BUCKET_NAME}/containers/"
