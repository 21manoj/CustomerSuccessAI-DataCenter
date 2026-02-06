#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         UPDATING TEST FILES TO USE NEW GENERATOR           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

TEST_FILES=(
    "test_onboarding_complete_e2e_api_v2.py"
    "test_customer19_e2e_onboarding.py"
    "test_onboarding_complete_e2e_api.py"
    "test_onboarding_complete_e2e.py"
    "test_onboarding_e2e_new_customer.py"
)

for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "Processing: $file"
        
        # Backup
        cp "$file" "${file}.backup_$(date +%Y%m%d)"
        
        # Check if it uses old generator
        if grep -q "generate_synthetic_custo     
        echo ""
    else
        echo "⚠️  $file not found"
        echo ""
    fi
done

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    UPDATE SUMMARY                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Test files have been backed up."
echo ""
echo "Next steps:"
echo "1. Review each test file marked with ⚠️"
echo "2. Update imports and generator calls"
echo "3. Test each file individually"
echo ""
