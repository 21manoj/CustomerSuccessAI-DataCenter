#!/usr/bin/env bash
# Provision a t3.large EC2 instance for CS Pulse V6 (platform + postgres only).
# Load driver runs from your laptop. SSL can be added with CloudFront (see docs).
#
# Prerequisites: AWS CLI configured (aws configure).
# Usage: ./scripts/provision-ec2-v6.sh [region]
# Optional env: CSPULSE_S3_BUCKET (for IAM role to pull images); KEY_NAME (SSH key).

set -e
AWS_REGION="${1:-us-east-1}"
INSTANCE_TYPE="t3.large"
KEY_NAME="${KEY_NAME:-cspulse-v6-key}"
SG_NAME="cspulse-v6-sg"
INSTANCE_NAME="cspulse-v6"
S3_BUCKET="${CSPULSE_S3_BUCKET:-cspulse-container-artifacts-$(aws sts get-caller-identity --query Account --output text 2>/dev/null)}"

echo "=== Provisioning EC2 for CS Pulse V6 (platform + postgres only) ==="
echo "  Region:       $AWS_REGION"
echo "  Instance:     $INSTANCE_TYPE (8 GB RAM)"
echo "  Security:     $SG_NAME"
echo "  Key:          $KEY_NAME"
echo "  S3 bucket:    $S3_BUCKET (for IAM role)"
echo ""

# Resolve latest Amazon Linux 2023 AMI
AMI_ID=$(aws ssm get-parameters \
  --names /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
  --region "$AWS_REGION" \
  --query 'Parameters[0].Value' --output text 2>/dev/null)
if [[ -z "$AMI_ID" ]]; then
  AMI_ID=$(aws ssm get-parameters \
    --names /aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2 \
    --region "$AWS_REGION" --query 'Parameters[0].Value' --output text)
fi
echo "  AMI:          $AMI_ID"
echo ""

# 1) Security group
if ! aws ec2 describe-security-groups --group-names "$SG_NAME" --region "$AWS_REGION" &>/dev/null; then
  aws ec2 create-security-group --group-name "$SG_NAME" \
    --description "CS Pulse V6: HTTP, HTTPS, SSH" --region "$AWS_REGION"
  echo "Created security group: $SG_NAME"
fi
SG_ID=$(aws ec2 describe-security-groups --group-names "$SG_NAME" --region "$AWS_REGION" --query 'SecurityGroups[0].GroupId' --output text)

for port in 22 80 443; do
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
    --protocol tcp --port "$port" --cidr 0.0.0.0/0 --region "$AWS_REGION" 2>/dev/null || true
done
echo "Security group rules: 22, 80, 443"

# 2) Key pair (create if missing; save .pem to repo root if new)
KEY_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/${KEY_NAME}.pem"
if ! aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$AWS_REGION" &>/dev/null; then
  aws ec2 create-key-pair --key-name "$KEY_NAME" --query 'KeyMaterial' --output text --region "$AWS_REGION" > "$KEY_FILE"
  chmod 400 "$KEY_FILE"
  echo "Created key pair: $KEY_NAME (saved to $KEY_FILE)"
else
  echo "Using existing key pair: $KEY_NAME"
fi

# 3) IAM role for S3 read (optional, so user-data can pull images)
INSTANCE_PROFILE=""
if [[ -n "$S3_BUCKET" ]] && [[ "$S3_BUCKET" != *"CHANGE_ME"* ]]; then
  ROLE_NAME="cspulse-v6-ec2-s3"
  if ! aws iam get-role --role-name "$ROLE_NAME" &>/dev/null; then
    aws iam create-role --role-name "$ROLE_NAME" \
      --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
    aws iam put-role-policy --role-name "$ROLE_NAME" --policy-name S3Read \
      --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\"],\"Resource\":[\"arn:aws:s3:::${S3_BUCKET}/*\"]}]}"
    echo "Created IAM role: $ROLE_NAME (S3 read on $S3_BUCKET)"
  fi
  PROFILE_NAME="cspulse-v6-ec2-profile"
  if ! aws iam get-instance-profile --instance-profile-name "$PROFILE_NAME" &>/dev/null; then
    aws iam create-instance-profile --instance-profile-name "$PROFILE_NAME"
    aws iam add-role-to-instance-profile --instance-profile-name "$PROFILE_NAME" --role-name "$ROLE_NAME"
    echo "Waiting 10s for instance profile to propagate..."
    sleep 10
  fi
  INSTANCE_PROFILE="--iam-instance-profile Name=$PROFILE_NAME"
fi

# 4) User-data: install Docker, pull from S3, load images, run only platform + postgres
USER_DATA=$(cat <<'USERDATA'
#!/bin/bash
set -e
dnf update -y
dnf install -y docker
systemctl start docker && systemctl enable docker
usermod -aG docker ec2-user

# Docker Compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -sSL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# AWS CLI for pulling from S3 (if instance profile present)
dnf install -y awscli 2>/dev/null || yum install -y awscli 2>/dev/null || true

BUCKET="CSPULSE_S3_BUCKET_PLACEHOLDER"
if command -v aws &>/dev/null && [ -n "$BUCKET" ] && [ "$BUCKET" != "CSPULSE_S3_BUCKET_PLACEHOLDER" ]; then
  aws s3 cp "s3://${BUCKET}/containers/cspulse-platform.tar.gz" /tmp/
  aws s3 cp "s3://${BUCKET}/containers/cspulse-postgres.tar.gz" /tmp/
  gunzip -c /tmp/cspulse-platform.tar.gz | docker load
  gunzip -c /tmp/cspulse-postgres.tar.gz | docker load
  rm -f /tmp/cspulse-platform.tar.gz /tmp/cspulse-postgres.tar.gz
fi

mkdir -p /home/ec2-user/cspulse
echo 'POSTGRES_PASSWORD=change-me-min-32-chars' > /home/ec2-user/cspulse/.env.example
echo 'SECRET_KEY=change-me-min-32-chars' >> /home/ec2-user/cspulse/.env.example
chown -R ec2-user:ec2-user /home/ec2-user/cspulse
USERDATA
)
# Inject bucket into user-data
USER_DATA="${USER_DATA//CSPULSE_S3_BUCKET_PLACEHOLDER/$S3_BUCKET}"
USER_DATA_B64=$(echo "$USER_DATA" | base64 -w 0 2>/dev/null || echo "$USER_DATA" | base64)

# 5) Launch instance
EXISTING=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=$INSTANCE_NAME" "Name=instance-state-name,Values=running,pending" \
  --query 'Reservations[*].Instances[*].InstanceId' --output text --region "$AWS_REGION")
if [[ -n "$EXISTING" ]]; then
  echo "Instance already running: $EXISTING"
  INSTANCE_ID="$EXISTING"
else
  INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    $INSTANCE_PROFILE \
    --user-data "$USER_DATA_B64" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=30,VolumeType=gp3}' \
    --query 'Instances[0].InstanceId' --output text --region "$AWS_REGION")
  echo "Launched instance: $INSTANCE_ID"
fi

echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$AWS_REGION"

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo ""
echo "=== EC2 ready ==="
echo "  Instance ID:  $INSTANCE_ID"
echo "  Public IP:    $PUBLIC_IP"
echo "  SSH:          ssh -i $KEY_FILE ec2-user@$PUBLIC_IP"
echo ""
echo "Next steps:"
echo "  1) Copy kpi-dashboard/.env to EC2 and upload docker-compose.production.yml (or use images from S3)."
echo "  2) On EC2: cd cspulse && copy .env from repo, then run the two containers (see docs/EC2_V6_TWO_IMAGES.md)."
echo "  3) For SSL at no extra cost: put CloudFront in front (origin http://$PUBLIC_IP:80). See docs/V6_DEPLOYMENT_CONFIRMATIONS.md."
echo "  4) Run load driver from your laptop: CS_PULSE_BASE_URL=http://$PUBLIC_IP (or https://your-domain after CloudFront)."
echo ""
