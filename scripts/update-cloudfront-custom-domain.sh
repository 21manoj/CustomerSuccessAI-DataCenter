#!/usr/bin/env bash
# Add a custom domain (alias) and ACM certificate to the CS Pulse CloudFront distribution.
# Use when your egress proxy blocks *.cloudfront.net; allowlist your domain instead.
#
# Prerequisites:
#   - ACM certificate in us-east-1 for the custom domain (validated).
#   - CNAME your domain → d2oqfugrb2ltg9.cloudfront.net (after running this).
#
# Usage:
#   CUSTOM_DOMAIN=mcp.yourcompany.com ACM_CERT_ARN=arn:aws:acm:us-east-1:ACCOUNT:certificate/ID ./scripts/update-cloudfront-custom-domain.sh
#
# Optional: CSPULSE_CLOUDFRONT_ID (default E2I8B0C6RDAOGT)

set -e
DIST_ID="${CSPULSE_CLOUDFRONT_ID:-E2I8B0C6RDAOGT}"
CUSTOM_DOMAIN="${CUSTOM_DOMAIN}"
ACM_CERT_ARN="${ACM_CERT_ARN}"

if [[ -z "$CUSTOM_DOMAIN" ]] || [[ -z "$ACM_CERT_ARN" ]]; then
  echo "Usage: CUSTOM_DOMAIN=mcp.yourcompany.com ACM_CERT_ARN=arn:aws:acm:us-east-1:ACCOUNT:certificate/ID $0"
  echo "  ACM cert must be in us-east-1 and validated for the domain."
  exit 1
fi

echo "Adding custom domain to CloudFront distribution $DIST_ID"
echo "  Alias:    $CUSTOM_DOMAIN"
echo "  ACM cert: $ACM_CERT_ARN"
echo ""

# Get current config; CloudFront API returns { ETag, DistributionConfig }
aws cloudfront get-distribution-config --id "$DIST_ID" --output json > /tmp/cf-get.json
ETAG=$(jq -r '.ETag' /tmp/cf-get.json)

# Build updated config: add Aliases and switch ViewerCertificate to ACM
# Must not send ETag inside the config body
jq --arg domain "$CUSTOM_DOMAIN" --arg cert "$ACM_CERT_ARN" '
  .DistributionConfig
  | .Aliases = { "Quantity": 1, "Items": [$domain] }
  | .ViewerCertificate = {
      "ACMCertificateArn": $cert,
      "SSLSupportMethod": "sni-only",
      "MinimumProtocolVersion": "TLSv1.2_2021",
      "CertificateSource": "acm"
    }
' /tmp/cf-get.json > /tmp/cf-distconfig.json

aws cloudfront update-distribution --id "$DIST_ID" --if-match "$ETAG" --distribution-config file:///tmp/cf-distconfig.json --output text
rm -f /tmp/cf-get.json /tmp/cf-distconfig.json

echo ""
echo "Done. Distribution is updating (5–15 min)."
echo "  Add a CNAME in your DNS: $CUSTOM_DOMAIN → d2oqfugrb2ltg9.cloudfront.net"
echo "  Then use: https://$CUSTOM_DOMAIN/ and https://$CUSTOM_DOMAIN/mcp"
