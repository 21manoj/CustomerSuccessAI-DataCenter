#!/bin/bash
# Quick DNS check script for V2 domain

echo "🔍 Checking DNS for customervaluesystem.triadpartners.ai"
echo "=========================================================="
echo ""

DOMAIN="customervaluesystem.triadpartners.ai"
EXPECTED_IP="3.84.178.121"

# Check with multiple DNS servers
echo "1️⃣  Google DNS (8.8.8.8):"
RESULT=$(dig @8.8.8.8 +short $DOMAIN | tail -1)
if [ "$RESULT" == "$EXPECTED_IP" ]; then
    echo "   ✅ $RESULT (CORRECT)"
else
    echo "   ❌ $RESULT (Expected: $EXPECTED_IP)"
fi

echo ""
echo "2️⃣  Cloudflare DNS (1.1.1.1):"
RESULT=$(dig @1.1.1.1 +short $DOMAIN | tail -1)
if [ "$RESULT" == "$EXPECTED_IP" ]; then
    echo "   ✅ $RESULT (CORRECT)"
else
    echo "   ❌ $RESULT (Expected: $EXPECTED_IP)"
fi

echo ""
echo "3️⃣  Authoritative DNS (ns1.dns-parking.com):"
RESULT=$(dig @ns1.dns-parking.com +short $DOMAIN | tail -1)
if [ "$RESULT" == "$EXPECTED_IP" ]; then
    echo "   ✅ $RESULT (CORRECT)"
else
    echo "   ❌ $RESULT (Expected: $EXPECTED_IP)"
fi

echo ""
echo "4️⃣  Your Local DNS:"
RESULT=$(dig +short $DOMAIN | tail -1)
if [ "$RESULT" == "$EXPECTED_IP" ]; then
    echo "   ✅ $RESULT (CORRECT)"
else
    echo "   ❌ $RESULT (Expected: $EXPECTED_IP)"
fi

echo ""
echo "=========================================================="

# Final verdict
FINAL_RESULT=$(dig +short $DOMAIN | tail -1)
if [ "$FINAL_RESULT" == "$EXPECTED_IP" ]; then
    echo "✅ DNS IS WORKING!"
    echo ""
    echo "Next step: Run SSL setup script"
    echo "  ssh -i kpi-dashboard-key.pem ec2-user@3.84.178.121"
    echo "  ./setup-v2-ssl.sh"
else
    echo "⏳ DNS NOT READY YET"
    echo ""
    echo "Please:"
    echo "  1. Verify A record in your DNS provider"
    echo "  2. Wait 5-30 minutes for propagation"
    echo "  3. Run this script again: ./check-v2-dns.sh"
fi
echo ""
