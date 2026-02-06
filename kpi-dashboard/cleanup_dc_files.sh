#!/bin/bash
# cleanup_dc_files.sh
# Removes all files with "_dc" suffix (bad code)
# Run from project root: bash cleanup_dc_files.sh

set -e  # Exit on error

echo "🧹 Starting cleanup of _dc files..."
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counter
removed_count=0
skipped_count=0

# Find all files with _dc in backend directory
echo "📂 Searching for _dc files in backend/..."
echo ""

# List of files to remove (found in your codebase)
DC_FILES=(
    "backend/alert_engine_dc.py"
    "backend/api_routes_dc.py"
    "backend/config_dc.py"
    "backend/data_models_dc.py"
    "backend/delete_dc_data.py"
    "backend/health_calculator_dc.py"
    "backend/kpi_calculator_dc.py"
    "backend/kpi_definitions_dc.py"
    "backend/playbooks_dc.py"
    "backend/utils_dc.py"
    "backend/verify_dc_data.py"
    "backend/check_dc_data.py"
    "backend/seed_dc_data.py"
    "backend/upload_dc_seed_excel.py"
    "backend/generate_dc_seed_excel.py"
)

# Check if running from project root
if [ ! -d "backend" ]; then
    echo -e "${RED}❌ Error: Must run from project root directory (where backend/ folder is)${NC}"
    exit 1
fi

# Backup option
echo -e "${YELLOW}⚠️  Do you want to create a backup before deleting? (y/n)${NC}"
read -r backup_choice

if [ "$backup_choice" = "y" ]; then
    backup_dir="backup_dc_files_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    echo -e "${GREEN}📦 Creating backup in $backup_dir/${NC}"
    echo ""
fi

# Remove each file
for file in "${DC_FILES[@]}"; do
    if [ -f "$file" ]; then
        if [ "$backup_choice" = "y" ]; then
            # Create backup directory structure
            backup_path="$backup_dir/$file"
            mkdir -p "$(dirname "$backup_path")"
            cp "$file" "$backup_path"
        fi
        
        rm "$file"
        echo -e "${GREEN}✅ Removed: $file${NC}"
        ((removed_count++))
    else
        echo -e "${YELLOW}⚠️  Not found (already removed?): $file${NC}"
        ((skipped_count++))
    fi
done

echo ""
echo "═══════════════════════════════════════════"
echo -e "${GREEN}✨ Cleanup Complete!${NC}"
echo "═══════════════════════════════════════════"
echo -e "Files removed: ${GREEN}$removed_count${NC}"
echo -e "Files not found: ${YELLOW}$skipped_count${NC}"

if [ "$backup_choice" = "y" ]; then
    echo -e "Backup location: ${GREEN}$backup_dir/${NC}"
fi

echo ""
echo "📋 Next steps:"
echo "1. Review the changes with: git status"
echo "2. Remove any _dc imports from other files"
echo "3. Check for any references to deleted modules"
echo ""

# Optional: Search for remaining _dc references
echo -e "${YELLOW}🔍 Searching for remaining _dc references in code...${NC}"
echo ""

# Search for imports of _dc modules
if grep -r "from.*_dc import\|import.*_dc" backend/ --include="*.py" 2>/dev/null; then
    echo ""
    echo -e "${RED}⚠️  Found _dc imports above! Clean these up manually.${NC}"
else
    echo -e "${GREEN}✅ No _dc imports found!${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Cleanup script finished!${NC}"
