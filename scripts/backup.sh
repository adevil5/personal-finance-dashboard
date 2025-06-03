#!/bin/bash
# Database backup script for Personal Finance Dashboard

# Load environment variables
source .env

# Set variables
DB_NAME="${DB_NAME:-finance_dashboard}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_backup_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to perform backup
perform_backup() {
    echo "Starting backup of database: $DB_NAME"
    echo "Backup file: $BACKUP_FILE"

    # Use pg_dump to create backup
    if [ -z "$DB_PASSWORD" ]; then
        # No password (local auth)
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$BACKUP_FILE" --verbose --clean --no-owner
    else
        # With password
        PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$BACKUP_FILE" --verbose --clean --no-owner
    fi

    if [ $? -eq 0 ]; then
        echo "Backup completed successfully!"

        # Compress the backup
        gzip "$BACKUP_FILE"
        echo "Backup compressed: ${BACKUP_FILE}.gz"

        # Clean up old backups (keep last 7 days)
        find "$BACKUP_DIR" -name "${DB_NAME}_backup_*.sql.gz" -mtime +7 -delete
        echo "Old backups cleaned up (kept last 7 days)"
    else
        echo "Backup failed!"
        exit 1
    fi
}

# Main execution
perform_backup
