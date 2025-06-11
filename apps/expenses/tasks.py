"""
Celery tasks for expense management.

Handles automated recurring transaction generation, file cleanup,
and other asynchronous operations.
"""

import logging
from datetime import date, timedelta

from celery import shared_task

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction

from apps.expenses.models import Transaction
from apps.expenses.storage import get_storage_backend

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_recurring_transactions(self, user_id: int = None) -> dict:
    """
    Generate all due recurring transactions.

    Args:
        user_id: Optional user ID to process only one user's transactions

    Returns:
        Dictionary with generation statistics
    """
    try:
        stats = {
            "processed": 0,
            "generated": 0,
            "errors": 0,
            "user_count": 0,
        }

        # Get transactions that are due for generation
        queryset = Transaction.objects.filter(
            is_recurring=True,
            is_active=True,
            next_occurrence__lte=date.today(),
        ).select_related("user", "category")

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Group by user for processing
        users_processed = set()

        for recurring_transaction in queryset:
            try:
                with db_transaction.atomic():
                    # Generate the next transaction
                    generated = recurring_transaction.generate_next_transaction()

                    if generated:
                        stats["generated"] += 1

                    stats["processed"] += 1
                    users_processed.add(recurring_transaction.user_id)

            except Exception as exc:
                stats["errors"] += 1
                # Log the error but continue processing other transactions
                self.retry(countdown=60, exc=exc)

        stats["user_count"] = len(users_processed)
        return stats

    except Exception as exc:
        # Log the error and retry
        raise self.retry(countdown=60, exc=exc)


@shared_task(bind=True)
def generate_user_recurring_transactions(self, user_id: int) -> dict:
    """
    Generate recurring transactions for a specific user.

    Args:
        user_id: ID of the user to process

    Returns:
        Dictionary with generation statistics
    """
    return generate_recurring_transactions.delay(user_id=user_id).get()


@shared_task
def cleanup_expired_recurring_transactions() -> dict:
    """
    Clean up recurring transactions that have passed their end date.

    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        "stopped": 0,
        "processed": 0,
    }

    # Find recurring transactions that have passed their end date
    expired_transactions = Transaction.objects.filter(
        is_recurring=True,
        is_active=True,
        recurring_end_date__lt=date.today(),
    )

    for transaction in expired_transactions:
        transaction.stop_recurring()
        stats["stopped"] += 1
        stats["processed"] += 1

    return stats


@shared_task
def generate_upcoming_recurring_transactions(days_ahead: int = 7) -> dict:
    """
    Pre-generate recurring transactions for the next N days.

    This is useful for ensuring transactions are available even if the
    system is down on the exact due date.

    Args:
        days_ahead: Number of days ahead to generate transactions

    Returns:
        Dictionary with generation statistics
    """
    stats = {
        "processed": 0,
        "generated": 0,
        "errors": 0,
    }

    future_date = date.today() + timedelta(days=days_ahead)

    # Get transactions due within the next N days
    upcoming_transactions = Transaction.objects.filter(
        is_recurring=True,
        is_active=True,
        next_occurrence__lte=future_date,
        next_occurrence__gt=date.today(),
    ).select_related("user", "category")

    for recurring_transaction in upcoming_transactions:
        try:
            with db_transaction.atomic():
                # Check if this transaction was already generated
                existing = Transaction.objects.filter(
                    parent_transaction=recurring_transaction,
                    date=recurring_transaction.next_occurrence,
                    is_active=True,
                ).exists()

                if not existing:
                    generated = recurring_transaction.generate_next_transaction()
                    if generated:
                        stats["generated"] += 1

                stats["processed"] += 1

        except Exception:
            stats["errors"] += 1

    return stats


@shared_task
def validate_recurring_transactions() -> dict:
    """
    Validate all recurring transactions for consistency.

    Returns:
        Dictionary with validation results
    """
    stats = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "fixed": 0,
        "errors": [],
    }

    # Get all active recurring transactions
    recurring_transactions = Transaction.objects.filter(
        is_recurring=True,
        is_active=True,
    )

    for transaction in recurring_transactions:
        stats["total"] += 1

        try:
            # Validate the transaction
            transaction.full_clean()

            # Check if next_occurrence is correctly calculated
            expected_next = transaction.calculate_next_occurrence()
            if transaction.next_occurrence != expected_next:
                # Fix the next occurrence
                transaction.next_occurrence = expected_next
                transaction.save(update_fields=["next_occurrence"])
                stats["fixed"] += 1

            stats["valid"] += 1

        except Exception as e:
            stats["invalid"] += 1
            stats["errors"].append(
                {
                    "transaction_id": transaction.id,
                    "error": str(e),
                }
            )

    return stats


# Periodic task configuration
# These would be configured in celery beat schedule


@shared_task(bind=True)
def cleanup_orphaned_files(self) -> dict:
    """
    Clean up files that are not referenced by any active transaction.

    Returns:
        Dictionary with cleanup statistics
    """
    try:
        # Get storage backend
        storage = get_storage_backend()

        logger.info("Starting orphaned files cleanup task")
        deleted_count = storage.cleanup_orphaned_files(dry_run=False)

        stats = {"success": True, "deleted_count": deleted_count, "error": None}

        logger.info(f"Orphaned files cleanup completed. Deleted {deleted_count} files")
        return stats

    except Exception as exc:
        logger.error(f"Orphaned files cleanup failed: {exc}")
        stats = {"success": False, "deleted_count": 0, "error": str(exc)}
        return stats


@shared_task(bind=True)
def cleanup_expired_files(self, retention_days: int = None) -> dict:
    """
    Clean up files older than the retention period.

    Args:
        retention_days: Days to retain files (uses default if None)

    Returns:
        Dictionary with cleanup statistics
    """
    try:
        # Get storage backend
        storage = get_storage_backend()

        logger.info(
            f"Starting expired files cleanup task (retention: {retention_days} days)"
        )
        deleted_count = storage.cleanup_expired_files(
            retention_days=retention_days, dry_run=False
        )

        stats = {
            "success": True,
            "deleted_count": deleted_count,
            "retention_days": retention_days or storage.retention_days,
            "error": None,
        }

        logger.info(f"Expired files cleanup completed. Deleted {deleted_count} files")
        return stats

    except Exception as exc:
        logger.error(f"Expired files cleanup failed: {exc}")
        stats = {
            "success": False,
            "deleted_count": 0,
            "retention_days": retention_days,
            "error": str(exc),
        }
        return stats


@shared_task(bind=True)
def cleanup_user_files(self, user_id: int) -> dict:
    """
    Clean up all files for a specific user (e.g., when user account is deleted).

    Args:
        user_id: ID of the user whose files should be deleted

    Returns:
        Dictionary with cleanup statistics
    """
    try:
        # Get storage backend
        storage = get_storage_backend()

        logger.info(f"Starting user files cleanup for user {user_id}")
        deleted_count = storage.cleanup_user_files(user_id, dry_run=False)

        stats = {
            "success": True,
            "deleted_count": deleted_count,
            "user_id": user_id,
            "error": None,
        }

        logger.info(
            f"User files cleanup completed for user {user_id}. "
            f"Deleted {deleted_count} files"
        )
        return stats

    except Exception as exc:
        logger.error(f"User files cleanup failed for user {user_id}: {exc}")
        stats = {
            "success": False,
            "deleted_count": 0,
            "user_id": user_id,
            "error": str(exc),
        }
        return stats


@shared_task(bind=True)
def rotate_file_encryption_keys(self, old_key_id: str, new_key_id: str) -> dict:
    """
    Rotate KMS encryption keys for all stored files.

    Args:
        old_key_id: Current KMS key ID
        new_key_id: New KMS key ID

    Returns:
        Dictionary with rotation statistics
    """
    try:
        # Get storage backend
        storage = get_storage_backend()

        # Check if storage supports key rotation (S3 only)
        if not hasattr(storage, "rotate_encryption_key"):
            logger.warning("Storage backend does not support encryption key rotation")
            return {
                "success": False,
                "error": "Storage backend does not support encryption key rotation",
            }

        logger.info(f"Starting encryption key rotation: {old_key_id} -> {new_key_id}")

        stats = {
            "success": True,
            "processed": 0,
            "rotated": 0,
            "errors": 0,
            "old_key_id": old_key_id,
            "new_key_id": new_key_id,
            "error": None,
        }

        # List all files and rotate keys
        continuation_token = None

        while True:
            list_params = {
                "Bucket": storage.bucket_name,
                "Prefix": "receipts/",
                "MaxKeys": storage.cleanup_batch_size,
            }

            if continuation_token:
                list_params["ContinuationToken"] = continuation_token

            response = storage.s3_client.list_objects_v2(**list_params)

            if "Contents" not in response:
                break

            for obj in response["Contents"]:
                file_key = obj["Key"]
                stats["processed"] += 1

                try:
                    success = storage.rotate_encryption_key(
                        file_key, old_key_id, new_key_id
                    )
                    if success:
                        stats["rotated"] += 1
                    else:
                        stats["errors"] += 1

                except Exception as e:
                    logger.error(f"Failed to rotate key for {file_key}: {e}")
                    stats["errors"] += 1

            # Check if there are more objects
            if not response.get("IsTruncated"):
                break

            continuation_token = response.get("NextContinuationToken")

        logger.info(
            f"Encryption key rotation completed. "
            f"Processed: {stats['processed']}, "
            f"Rotated: {stats['rotated']}, "
            f"Errors: {stats['errors']}"
        )
        return stats

    except Exception as exc:
        logger.error(f"Encryption key rotation failed: {exc}")
        stats = {
            "success": False,
            "processed": 0,
            "rotated": 0,
            "errors": 0,
            "old_key_id": old_key_id,
            "new_key_id": new_key_id,
            "error": str(exc),
        }
        return stats


def get_recurring_transaction_schedules() -> dict:
    """
    Get the periodic task schedules for recurring transactions.

    This function returns the schedule configuration that should be
    added to CELERY_BEAT_SCHEDULE in settings.
    """
    return {
        "generate-recurring-transactions": {
            "task": "apps.expenses.tasks.generate_recurring_transactions",
            "schedule": 60.0 * 60,  # Every hour
            "options": {"queue": "recurring"},
        },
        "cleanup-expired-recurring": {
            "task": "apps.expenses.tasks.cleanup_expired_recurring_transactions",
            "schedule": 60.0 * 60 * 24,  # Daily
            "options": {"queue": "maintenance"},
        },
        "validate-recurring-transactions": {
            "task": "apps.expenses.tasks.validate_recurring_transactions",
            "schedule": 60.0 * 60 * 24,  # Daily
            "options": {"queue": "maintenance"},
        },
        "cleanup-orphaned-files": {
            "task": "apps.expenses.tasks.cleanup_orphaned_files",
            "schedule": 60.0 * 60 * 24,  # Daily
            "options": {"queue": "maintenance"},
        },
        "cleanup-expired-files": {
            "task": "apps.expenses.tasks.cleanup_expired_files",
            "schedule": 60.0 * 60 * 24 * 7,  # Weekly
            "options": {"queue": "maintenance"},
        },
    }
