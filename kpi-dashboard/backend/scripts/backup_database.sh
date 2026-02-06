#!/bin/bash
#
# Database Backup Script
# Creates a timestamped backup of the PostgreSQL database
#

set -e

# Configuration
DB_NAME="${DB_NAME:-cspulse_db}"
DB_USER="${DB_USER:-dcuser}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "Database Backup"
echo "=========================================="
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "Backup file: $BACKUP_FILE"
echo ""

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    echo "❌ Error: pg_dump not found"
    echo "   Please install PostgreSQL client tools"
    exit 1
fi

# Perform backup
echo "Creating backup..."
PGPASSWORD="${DB_PASS:-dcpass123}" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --no-owner \
    --no-acl \
    -F p \
    > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Get file size
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    echo "✅ Backup created successfully!"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $FILE_SIZE"
    echo ""
    
    # Create a symlink to latest backup
    LATEST_LINK="${BACKUP_DIR}/backup_latest.sql"
    ln -sf "$(basename "$BACKUP_FILE")" "$LATEST_LINK"
    echo "✅ Latest backup link: $LATEST_LINK"
    
    exit 0
else
    echo "❌ Backup failed!"
    exit 1
fi
