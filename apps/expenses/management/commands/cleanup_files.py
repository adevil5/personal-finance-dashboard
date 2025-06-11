"""
Management command for cleaning up uploaded files.

This command provides various file cleanup operations:
- Remove orphaned files not referenced by any transaction
- Remove expired files older than retention period
- Remove all files for a specific user
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.expenses.storage import get_storage_backend

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command for file cleanup operations."""

    help = "Clean up uploaded files (orphaned, expired, or user-specific)"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--type",
            choices=["orphaned", "expired", "user"],
            required=True,
            help="Type of cleanup to perform",
        )

        parser.add_argument(
            "--user-id",
            type=int,
            help="User ID for user-specific cleanup (required for --type=user)",
        )

        parser.add_argument(
            "--retention-days",
            type=int,
            default=365,
            help="Retention period in days for expired files cleanup (default: 365)",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of files to process in each batch (default: 1000)",
        )

    def handle(self, *args, **options):
        """Execute the cleanup command."""
        cleanup_type = options["type"]
        dry_run = options["dry_run"]

        # Get appropriate storage backend
        storage = get_storage_backend()

        # Update batch size if provided
        if options["batch_size"]:
            storage.cleanup_batch_size = options["batch_size"]

        try:
            if cleanup_type == "orphaned":
                deleted_count = self._cleanup_orphaned_files(storage, dry_run)

            elif cleanup_type == "expired":
                retention_days = options["retention_days"]
                deleted_count = self._cleanup_expired_files(
                    storage, retention_days, dry_run
                )

            elif cleanup_type == "user":
                user_id = options.get("user_id")
                if not user_id:
                    raise CommandError("--user-id is required for user cleanup")
                deleted_count = self._cleanup_user_files(storage, user_id, dry_run)

            # Report results
            action = "Would delete" if dry_run else "Deleted"
            self.stdout.write(self.style.SUCCESS(f"{action} {deleted_count} files"))

        except Exception as e:
            logger.error(f"File cleanup failed: {e}")
            raise CommandError(f"Cleanup failed: {e}")

    def _cleanup_orphaned_files(self, storage, dry_run):
        """Clean up orphaned files."""
        self.stdout.write("Starting orphaned files cleanup...")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No files will be actually deleted")
            )

        deleted_count = storage.cleanup_orphaned_files(dry_run=dry_run)

        self.stdout.write("Orphaned files cleanup completed.")
        return deleted_count

    def _cleanup_expired_files(self, storage, retention_days, dry_run):
        """Clean up expired files."""
        self.stdout.write(
            f"Starting expired files cleanup (retention: {retention_days} days)..."
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No files will be actually deleted")
            )

        deleted_count = storage.cleanup_expired_files(
            retention_days=retention_days, dry_run=dry_run
        )

        self.stdout.write("Expired files cleanup completed.")
        return deleted_count

    def _cleanup_user_files(self, storage, user_id, dry_run):
        """Clean up files for a specific user."""
        self.stdout.write(f"Starting user files cleanup for user {user_id}...")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE: No files will be actually deleted")
            )

        # Confirm user deletion in production (when not dry run)
        if not dry_run:
            confirmation = input(
                f"Are you sure you want to delete ALL files for user {user_id}? "
                "This action cannot be undone. Type 'yes' to confirm: "
            )
            if confirmation.lower() != "yes":
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return 0

        deleted_count = storage.cleanup_user_files(user_id, dry_run=dry_run)

        self.stdout.write(f"User files cleanup completed for user {user_id}.")
        return deleted_count
