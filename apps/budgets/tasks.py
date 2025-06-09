"""
Celery tasks for budget alerts and notifications.
"""

import logging

from celery import shared_task

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from .models import Budget, BudgetAlert
from .notifications import BudgetNotificationService

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def check_budget_alerts(self) -> dict:
    """
    Check all active budgets for alert conditions and generate alerts.

    This task should be run periodically (e.g., daily) to check if any budgets
    have crossed their warning or critical thresholds.

    Returns:
        dict: Summary of alerts checked and generated
    """
    try:
        # Get all active budgets with alerts enabled
        active_budgets = (
            Budget.objects.filter(
                is_active=True,
                alert_enabled=True,
            )
            .select_related("user")
            .prefetch_related("alerts")
        )

        total_budgets = active_budgets.count()
        alerts_generated = 0
        budgets_with_alerts = 0

        logger.info(f"Checking {total_budgets} active budgets for alert conditions")

        for budget in active_budgets:
            try:
                # Generate alerts for this budget
                new_alerts = budget.generate_alerts()

                if new_alerts:
                    alerts_generated += len(new_alerts)
                    budgets_with_alerts += 1
                    logger.info(
                        f"Generated {len(new_alerts)} alerts for budget {budget.name}"
                    )

                    # Send notifications for new alerts
                    notification_count = (
                        BudgetNotificationService.send_budget_notifications_batch(
                            new_alerts
                        )
                    )
                    logger.info(
                        f"Sent {notification_count} notifications for budget {budget.name}"
                    )

            except Exception as e:
                logger.error(f"Error processing budget {budget.id}: {e}")
                continue

        summary = {
            "total_budgets_checked": total_budgets,
            "budgets_with_new_alerts": budgets_with_alerts,
            "total_alerts_generated": alerts_generated,
            "task_completed_at": timezone.now().isoformat(),
        }

        logger.info(f"Budget alert check completed: {summary}")
        return summary

    except Exception as exc:
        logger.error(f"Budget alert check task failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(
            exc=exc, countdown=60 * (2**self.request.retries)
        )


@shared_task(bind=True, max_retries=3)
def send_daily_budget_summaries(self) -> dict:
    """
    Send daily budget summaries to users with active alerts.

    This task should be run once daily to send summary emails to users
    who have active budget alerts.

    Returns:
        dict: Summary of summaries sent
    """
    try:
        # Get users with active alerts
        users_with_alerts = BudgetNotificationService.get_users_with_active_alerts()

        total_users = len(users_with_alerts)
        summaries_sent = 0

        logger.info(
            f"Sending daily summaries to {total_users} users with active alerts"
        )

        for user in users_with_alerts:
            try:
                if BudgetNotificationService.send_daily_budget_summary(user):
                    summaries_sent += 1
            except Exception as e:
                logger.error(f"Error sending daily summary to user {user.id}: {e}")
                continue

        summary = {
            "total_users_with_alerts": total_users,
            "summaries_sent": summaries_sent,
            "task_completed_at": timezone.now().isoformat(),
        }

        logger.info(f"Daily budget summaries completed: {summary}")
        return summary

    except Exception as exc:
        logger.error(f"Daily budget summaries task failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task
def process_budget_alert_for_transaction(transaction_id: int) -> bool:
    """
    Process budget alerts when a new transaction is created.

    This task is triggered when a new expense transaction is created
    to immediately check if any budget thresholds have been crossed.

    Args:
        transaction_id: ID of the transaction that was created

    Returns:
        bool: True if processing was successful
    """
    try:
        from apps.expenses.models import Transaction

        transaction = Transaction.objects.select_related("user", "category").get(
            id=transaction_id
        )

        # Only process expense transactions
        if transaction.transaction_type != Transaction.EXPENSE:
            return True

        # Get budgets that might be affected by this transaction
        affected_budgets = Budget.objects.filter(
            user=transaction.user,
            is_active=True,
            alert_enabled=True,
            period_start__lte=transaction.date,
            period_end__gte=transaction.date,
        ).filter(
            # Either budget is for the specific category or is an overall budget (no category)
            models.Q(category=transaction.category)
            | models.Q(category__isnull=True)
        )

        alerts_generated = 0

        for budget in affected_budgets:
            try:
                new_alerts = budget.generate_alerts()

                if new_alerts:
                    alerts_generated += len(new_alerts)
                    # Send immediate notifications for new alerts
                    BudgetNotificationService.send_budget_notifications_batch(
                        new_alerts
                    )
                    logger.info(
                        f"Generated {len(new_alerts)} alerts for "
                        f"budget {budget.name} after transaction {transaction_id}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing alerts for budget {budget.id} "
                    f"after transaction {transaction_id}: {e}"
                )
                continue

        logger.info(
            f"Processed budget alerts for transaction {transaction_id}, "
            f"generated {alerts_generated} alerts"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to process budget alerts for "
            f"transaction {transaction_id}: {e}"
        )
        return False


@shared_task
def resolve_outdated_alerts() -> dict:
    """
    Resolve alerts for budgets where spending has dropped below thresholds.

    This task cleans up alerts that are no longer relevant because
    spending has decreased (e.g., due to refunds or transaction corrections).

    Returns:
        dict: Summary of alerts resolved
    """
    try:
        # Get all unresolved alerts
        active_alerts = BudgetAlert.objects.filter(is_resolved=False).select_related(
            "budget"
        )

        resolved_count = 0

        for alert in active_alerts:
            budget = alert.budget

            # Check if the alert condition still applies
            should_have_warning = budget.should_trigger_warning_alert()
            should_have_critical = budget.should_trigger_critical_alert()

            should_resolve = False

            if (
                alert.alert_type == BudgetAlert.WARNING
                and not should_have_warning
            ):
                should_resolve = True
            elif (
                alert.alert_type == BudgetAlert.CRITICAL
                and not should_have_critical
            ):
                should_resolve = True

            if should_resolve:
                alert.mark_as_resolved()
                resolved_count += 1
                logger.info(
                    f"Resolved outdated {alert.alert_type} alert "
                    f"for budget {budget.name}"
                )

        summary = {
            "alerts_checked": active_alerts.count(),
            "alerts_resolved": resolved_count,
            "task_completed_at": timezone.now().isoformat(),
        }

        logger.info(f"Outdated alert resolution completed: {summary}")
        return summary

    except Exception as e:
        logger.error(f"Failed to resolve outdated alerts: {e}")
        return {"error": str(e)}
