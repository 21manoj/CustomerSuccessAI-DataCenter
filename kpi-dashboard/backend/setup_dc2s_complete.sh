#!/bin/bash
# Complete DC2_S User Setup Script
# Creates user dc_super1 and all 10 accounts

echo "=========================================="
echo "DC2_S USER & ACCOUNTS SETUP"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Create user: dc_super1 (password: dc_super321)"
echo "  2. Create 10 DC2_S sample accounts with KPIs"
echo "  3. Verify login and access"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled"
    exit 1
fi

cd /Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend

echo ""
echo "=========================================="
echo "Step 1: Creating DC2_S User & Accounts"
echo "=========================================="
python3 create_dc2s_user.py

if [ $? -ne 0 ]; then
    echo "❌ Setup failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "Step 2: Testing Login"
echo "=========================================="
python3 test_dc_login.py

if [ $? -ne 0 ]; then
    echo "❌ Login test failed!"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Login Credentials:"
echo "  Username: dc_super1"
echo "  Password: dc_super321"
echo "  URL: http://localhost:3000/login"
echo ""
echo "What's Created:"
echo "  ✅ 1 super user (full access)"
echo "  ✅ 10 DC2_S accounts"
echo "  ✅ ~120 KPIs across all accounts"
echo "  ✅ Health scores calculated"
echo ""
echo "Next Steps:"
echo "  1. Start backend: cd backend && python3 app.py"
echo "  2. Start frontend: cd frontend && npm start"
echo "  3. Login at: http://localhost:3000"
echo "  4. Navigate to: DC2_S Dashboard"
echo ""
echo "Account Summary:"
echo "  🟢 3 Healthy accounts (75-100 health)"
echo "  🟡 4 Risk accounts (50-75 health)"
echo "  🔴 3 Critical accounts (0-50 health)"
echo ""
