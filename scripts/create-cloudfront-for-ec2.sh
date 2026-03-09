#!/usr/bin/env bash
# Create a CloudFront distribution in front of the CS Pulse EC2 instance.
# - Viewers get HTTPS (redirect HTTP -> HTTPS).
# - Origin (EC2) stays HTTP; no SSL on EC2.
# - Uses default CloudFront certificate (*.cloudfront.net). For custom domain, add ACM cert and CNAME (see doc).
set -e

# CloudFront requires a hostname; IP is not allowed. Use EC2 public DNS (us-east-1 pattern).
ORIGIN_HOST="${ORIGIN_HOST:-ec2-3-81-222-159.compute-1.amazonaws.com}"

CALLER_REF="cspulse-ec2-$(date +%s)"
DIST_CONFIG=$(cat <<EOF
{
  "CallerReference": "${CALLER_REF}",
  "Comment": "CS Pulse EC2 - HTTPS in front of origin",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "cspulse-ec2-origin",
        "DomainName": "${ORIGIN_HOST}",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginSslProtocols": { "Quantity": 1, "Items": ["TLSv1.2"] }
        },
        "ConnectionAttempts": 3,
        "ConnectionTimeout": 10
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "cspulse-ec2-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 7,
      "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
      "CachedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] }
    },
    "Compress": true,
    "MinTTL": 0,
    "DefaultTTL": 0,
    "MaxTTL": 0,
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": { "Forward": "all" },
      "Headers": { "Quantity": 3, "Items": ["Host", "Authorization", "Content-Type"] }
    }
  },
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": true
  },
  "PriceClass": "PriceClass_100"
}
EOF
)

echo "Creating CloudFront distribution (origin: http://${ORIGIN_HOST})..."
OUT=$(aws cloudfront create-distribution --distribution-config "$DIST_CONFIG")
DIST_ID=$(echo "$OUT" | jq -r '.Distribution.Id')
DOMAIN=$(echo "$OUT" | jq -r '.Distribution.DomainName')
STATUS=$(echo "$OUT" | jq -r '.Distribution.Status')

echo ""
echo "Distribution created."
echo "  Id:     ${DIST_ID}"
echo "  Domain: ${DOMAIN}"
echo "  Status: ${STATUS}"
echo ""
echo "Use this URL once the distribution is deployed (5–10 min):"
echo "  https://${DOMAIN}"
echo ""
echo "Optional: custom domain + ACM"
echo "  1. Request ACM certificate in us-east-1 for your domain."
echo "  2. aws cloudfront update-distribution --id ${DIST_ID} ... (add Aliases + ACMCertificateArn)."
echo "  3. CNAME your domain to ${DOMAIN}."
echo ""
echo "After switching to HTTPS, set SESSION_COOKIE_SECURE=true on EC2 (remove SESSION_COOKIE_SECURE=false from .env)."
