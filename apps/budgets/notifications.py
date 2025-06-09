"""
Budget alert notification system.

Handles sending notifications when budget alerts are triggered.
"""

import logging
from typing import List

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from .models import BudgetAlert

logger = logging.getLogger(__name__)
User = get_user_model()


class BudgetNotificationService:
    """Service for sending budget alert notifications."""

    @staticmethod
    def send_alert_notification(alert: BudgetAlert) -> bool:
        """
        Send a notification for a budget alert.

        Args:
            alert: The BudgetAlert instance to send notification for

        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            user = alert.budget.user

            # Skip if user doesn't have email
            if not user.email:
                logger.warning(
                    f"User {user.id} has no email address for alert notification"
                )
                return False

            subject = f"Budget Alert: {alert.budget.name}"

            # Create email content
            context = {
                "user": user,
                "alert": alert,
                "budget": alert.budget,
                "utilization_percentage": alert.triggered_at_percentage,
                "spent_amount": alert.budget.calculate_spent_amount(),
                "budget_amount": alert.budget.amount,
                "remaining_amount": alert.budget.calculate_remaining_amount(),
            }

            # Try to render template, fall back to plain text if template doesn't exist
            try:
                message = render_to_string("budgets/emails/budget_alert.txt", context)
            except Exception:
                message = BudgetNotificationService._create_plain_text_message(alert)

            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            logger.info(
                f"Budget alert notification sent to {user.email} "
                f"for budget {alert.budget.name}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send budget alert notification: {e}")
            return False

    @staticmethod
    def _create_plain_text_message(alert: BudgetAlert) -> str:
        """Create a plain text alert message as fallback."""
        budget = alert.budget
        spent = budget.calculate_spent_amount()
        remaining = budget.calculate_remaining_amount()

        message = f"""
Budget Alert: {budget.name}

Hello {budget.user.first_name or budget.user.username},

Your budget "{budget.name}" has triggered a {alert.alert_type.lower()} alert.

Alert Details:
- Alert Type: {alert.alert_type}
- Budget Amount: ${budget.amount}
- Spent Amount: ${spent}
- Remaining Amount: ${remaining}
- Utilization: {alert.triggered_at_percentage}%

Budget Period: {budget.period_start} to {budget.period_end}

Please review your spending to stay within your budget limits.

Best regards,
Personal Finance Dashboard
        """.strip()

        return message

    @staticmethod
    def send_daily_budget_summary(user: User) -> bool:
        """
        Send a daily summary of budget alerts for a user.

        Args:
            user: The User to send summary for

        Returns:
            bool: True if summary was sent successfully, False otherwise
        """
        try:
            # Get active alerts from the last 24 hours
            yesterday = timezone.now() - timezone.timedelta(days=1)
            recent_alerts = (
                BudgetAlert.objects.filter(
                    budget__user=user,
                    is_resolved=False,
                    created_at__gte=yesterday,
                )
                .select_related("budget")
                .order_by("-created_at")
            )

            if not recent_alerts.exists():
                return True  # No alerts to send

            if not user.email:
                logger.warning(f"User {user.id} has no email address for daily summary")
                return False

            subject = "Daily Budget Alert Summary"

            context = {
                "user": user,
                "alerts": recent_alerts,
                "alert_count": recent_alerts.count(),
            }

            # Try to render template, fall back to plain text if template doesn't exist
            try:
                message = render_to_string("budgets/emails/daily_summary.txt", context)
            except Exception:
                message = BudgetNotificationService._create_daily_summary_message(
                    user, recent_alerts
                )

            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            logger.info(f"Daily budget summary sent to {user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send daily budget summary: {e}")
            return False

    @staticmethod
    def _create_daily_summary_message(user: User, alerts: List[BudgetAlert]) -> str:
        """Create a plain text daily summary message as fallback."""
        message_lines = [
            "Daily Budget Alert Summary",
            "",
            f"Hello {user.first_name or user.username},",
            "",
            f"You have {alerts.count()} active budget alerts:",
            "",
        ]

        for alert in alerts:
            budget = alert.budget
            message_lines.extend(
                [
                    f"• {budget.name} - {alert.alert_type} alert",
                    f"  Utilization: {alert.triggered_at_percentage}%",
                    f"  Spent: ${budget.calculate_spent_amount()} of ${budget.amount}",
                    "",
                ]
            )

        message_lines.extend(
            [
                "Please review your budgets and spending.",
                "",
                "Best regards,",
                "Personal Finance Dashboard",
            ]
        )

        return "\n".join(message_lines)

    @staticmethod
    def send_budget_notifications_batch(alerts: List[BudgetAlert]) -> int:
        """
        Send notifications for a batch of alerts.

        Args:
            alerts: List of BudgetAlert instances to send notifications for

        Returns:
            int: Number of notifications sent successfully
        """
        sent_count = 0

        for alert in alerts:
            if BudgetNotificationService.send_alert_notification(alert):
                sent_count += 1

        logger.info(f"Sent {sent_count} of {len(alerts)} budget alert notifications")
        return sent_count

    @staticmethod
    def get_users_with_active_alerts() -> List[User]:
        """Get all users who have active budget alerts."""
        return User.objects.filter(budgets__alerts__is_resolved=False).distinct()

    @staticmethod
    def mark_notifications_sent(alerts: List[BudgetAlert]) -> None:
        """
        Mark alerts as having notifications sent.

        This could be extended to track notification status if needed.
        """
        # For now, we just log that notifications were processed
        alert_ids = [alert.id for alert in alerts]
        logger.info(f"Marked notifications as sent for alerts: {alert_ids}")
