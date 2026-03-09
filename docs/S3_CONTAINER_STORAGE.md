# S3 bucket for container artifacts (50 GB planned)

Use this bucket to store Docker image tarballs (e.g. from `docker save`) or other deployment artifacts before or alongside ECR. S3 does **not** require reserving space—billing is pay-per-use; plan for ~50 GB.

## Prerequisites

- AWS CLI installed and configured (`aws configure` with credentials that can create S3 buckets).
- Choose a **bucket name** (globally unique) and **region** (e.g. `us-east-1`).

## One-time setup: create the bucket

Run from repo root (or run the script):

```bash
./scripts/aws-s3-container-bucket.sh
```

Or manually:

```bash
# Set these (bucket name must be globally unique)
AWS_REGION=us-east-1
BUCKET_NAME=cspulse-container-artifacts-$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "YOUR_ACCOUNT_ID")

# Create bucket
aws s3 mb "s3://${BUCKET_NAME}" --region "$AWS_REGION"

# Optional: enable versioning (recommended for artifacts)
aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled

# Optional: block public access (default for new buckets; ensure it stays off)
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Pushing image tarballs to S3 (example)

After building images locally:

```bash
# Save images to tarballs
docker save cspulse-platform:latest | gzip > cspulse-platform.tar.gz
docker save cspulse-postgres:latest | gzip > cspulse-postgres.tar.gz
docker save cspulse-load-driver:latest | gzip > cspulse-load-driver.tar.gz

# Upload (replace BUCKET_NAME with your bucket)
aws s3 cp cspulse-platform.tar.gz "s3://${BUCKET_NAME}/containers/"
aws s3 cp cspulse-postgres.tar.gz "s3://${BUCKET_NAME}/containers/"
aws s3 cp cspulse-load-driver.tar.gz "s3://${BUCKET_NAME}/containers/"
```

## Cost (rough, us-east-1)

- **Storage:** ~$0.023/GB/month → 50 GB ≈ **$1.15/month**.
- **PUT/GET:** Small for a few uploads/downloads; first 100 GB transfer out/month often free to internet (see AWS S3 pricing).

## After moving to ECR

Once images are in ECR, you can delete or archive objects in this bucket to reduce cost. Keep the bucket if you use it for backups or other artifacts.
