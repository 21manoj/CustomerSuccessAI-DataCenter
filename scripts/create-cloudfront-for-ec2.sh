#!/usr/bin/env bash
# Create a CloudFront distribution in front of the CS Pulse EC2 instance.
# - Viewers get HTTPS (redirect HTTP -> HTTPS). Clients never use :8001 on the CloudFront hostname;
#   edge listens on 443 only. /mcp* is routed to a second origin on EC2 port 8001 (MCP streamable HTTP).
# - Main origin (EC2) stays HTTP :80; MCP origin HTTP :8001. No SSL on EC2.
# - Open EC2 security group TCP 8001 for CloudFront (or 0.0.0.0/0 for demos) so the MCP origin works.
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
    "Quantity": 2,
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
      },
      {
        "Id": "cspulse-mcp-origin",
        "DomainName": "${ORIGIN_HOST}",
        "CustomOriginConfig": {
          "HTTPPort": 8001,
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
    "TrustedSigners": { "Enabled": false, "Quantity": 0 },
    "TrustedKeyGroups": { "Enabled": false, "Quantity": 0 },
    "AllowedMethods": {
      "Quantity": 7,
      "Items": ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"],
      "CachedMethods": { "Quantity": 2, "Items": ["GET", "HEAD"] }
    },
    "SmoothStreaming": false,
    "Compress": true,
    "LambdaFunctionAssociations": { "Quantity": 0 },
    "FunctionAssociations": { "Quantity": 0 },
    "FieldLevelEncryptionId": "",
    "GrpcConfig": { "Enabled": false },
    "MinTTL": 0,
    "DefaultTTL": 0,
    "MaxTTL": 0,
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": { "Forward": "all" },
      "Headers": { "Quantity": 3, "Items": ["Host", "Authorization", "Content-Type"] }
    }
  },
  "CacheBehaviors": {
    "Quantity": 1,
    "Items": [
      {
        "PathPattern": "/mcp*",
        "TargetOriginId": "cspulse-mcp-origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "TrustedSigners": { "Enabled": false, "Quantity": 0 },
        "TrustedKeyGroups": { "Enabled": false, "Quantity": 0 },
        "AllowedMethods": {
          "Quantity": 7,
          "Items": ["HEAD", "DELETE", "POST", "GET", "OPTIONS", "PUT", "PATCH"],
          "CachedMethods": { "Quantity": 2, "Items": ["HEAD", "GET"] }
        },
        "SmoothStreaming": false,
        "Compress": false,
        "LambdaFunctionAssociations": { "Quantity": 0 },
        "FunctionAssociations": { "Quantity": 0 },
        "FieldLevelEncryptionId": "",
        "GrpcConfig": { "Enabled": false },
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 0,
        "ForwardedValues": {
          "QueryString": true,
          "Cookies": { "Forward": "all" },
          "Headers": {
            "Quantity": 5,
            "Items": ["Authorization", "Accept", "Host", "Content-Type", "Mcp-Session-Id"]
          }
        }
      }
    ]
  },
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": true
  },
  "PriceClass": "PriceClass_100"
}
EOF
)

echo "Creating CloudFront distribution (origins: http://${ORIGIN_HOST}:80 app, :8001 /mcp*)..."
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
echo "MCP (streamable HTTP; viewer still uses :443, origin uses :8001):"
echo "  https://${DOMAIN}/mcp"
echo ""
echo "Optional: custom domain + ACM"
echo "  1. Request ACM certificate in us-east-1 for your domain."
echo "  2. aws cloudfront update-distribution --id ${DIST_ID} ... (add Aliases + ACMCertificateArn)."
echo "  3. CNAME your domain to ${DOMAIN}."
echo ""
echo "After switching to HTTPS, set SESSION_COOKIE_SECURE=true on EC2 (remove SESSION_COOKIE_SECURE=false from .env)."
