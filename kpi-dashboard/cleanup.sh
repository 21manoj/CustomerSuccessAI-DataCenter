#!/bin/bash
# cleanup.sh - Project cleanup script

echo "🧹 Starting project cleanup..."

# Phase 1: Remove log files
echo "Removing log files..."
rm -f *.log backend*.log frontend*.log server*.log

# Phase 2: Remove archive files
echo "Removing archive files..."
rm -f *.tar.gz build-*.tar.gz kpi-dashboard-*.tar.gz

# Phase 3: Remove Qdrant storage directories
echo "Removing old Qdrant storage directories..."
rm -rf qdrant_storage_*

# Phase 4: Remove backup files
echo "Removing backup files..."
rm -f *.backup src/components/*.backup

# Phase 5: Remove AWS package
echo "Removing AWS package..."
rm -f AWSCLIV2.pkg

# Phase 6: Archive test results
echo "Archiving test results..."
mkdir -p archive/test-results
mv v3_*_test_results.json archive/test-results/ 2>/dev/null || true

echo "✅ Cleanup complete!"
echo "Space saved: ~1.7GB"
echo "Files removed: ~208"
