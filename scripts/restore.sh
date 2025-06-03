#!/bin/bash
# Database restore script for Personal Finance Dashboard

# Load environment variables
source .env

# Set variables
DB_NAME="${DB_NAME:-finance_dashboard}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="./backups"

# Function to list available backups
list_backups() {
    echo "Available backups:"
    ls -1 "$BACKUP_DIR"/${DB_NAME}_backup_*.sql.gz 2>/dev/null | sort -r
}

# Function to perform restore
perform_restore() {
    local backup_file=$1

    if [ ! -f "$backup_file" ]; then
        echo "Error: Backup file not found: $backup_file"
        exit 1
    fi

    echo "WARNING: This will restore the database from: $backup_file"
    echo "This will OVERWRITE all current data in database: $DB_NAME"
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled."
        exit 0
    fi

    # Create temporary uncompressed file
    temp_file="${backup_file%.gz}.tmp"
    echo "Decompressing backup..."
    gunzip -c "$backup_file" > "$temp_file"

    echo "Starting restore of database: $DB_NAME"

    # Use psql to restore
    if [ -z "$DB_PASSWORD" ]; then
        # No password (local auth)
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$temp_file"
    else
        # With password
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$temp_file"
    fi

    if [ $? -eq 0 ]; then
        echo "Restore completed successfully!"
    else
        echo "Restore failed!"
        rm -f "$temp_file"
        exit 1
    fi

    # Clean up temporary file
    rm -f "$temp_file"
}

# Main execution
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo ""
    list_backups
    exit 1
fi

perform_restore "$1"
