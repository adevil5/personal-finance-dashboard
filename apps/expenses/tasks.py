"""
Celery tasks for expense management.

Handles automated recurring transaction generation and other asynchronous operations.
"""

from datetime import date, timedelta

from celery import shared_task

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction

from apps.expenses.models import Transaction

User = get_user_model()


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
    }
