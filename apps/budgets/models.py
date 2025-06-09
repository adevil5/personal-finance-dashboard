from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum

from apps.core.security.fields import EncryptedDecimalField

User = get_user_model()


class Budget(models.Model):
    """
    Budget model for tracking spending budgets.

    Supports category-specific budgets and overall budgets (without category).
    Includes period-based tracking with dynamic spent amount calculations.
    Uses encrypted amount field for secure storage of financial information.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="budgets",
        help_text="User this budget belongs to",
    )

    category = models.ForeignKey(
        "expenses.Category",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="budgets",
        help_text="Category for this budget (optional for overall budgets)",
    )

    name = models.CharField(
        max_length=255,
        help_text="Budget name or description",
    )

    amount = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Budget amount (encrypted)",
    )

    amount_index = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Budget amount for filtering/sorting (non-encrypted)",
    )

    period_start = models.DateField(
        help_text="Budget period start date",
    )

    period_end = models.DateField(
        help_text="Budget period end date",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this budget is active (soft delete)",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this budget was created",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this budget was last updated",
    )

    # Alert configuration fields
    alert_enabled = models.BooleanField(
        default=False,
        help_text="Whether alerts are enabled for this budget",
    )

    warning_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Warning alert threshold as percentage (e.g., 80.00 for 80%)",
    )

    critical_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Critical alert threshold as percentage (e.g., 100.00 for 100%)",
    )

    class Meta:
        db_table = "budgets_budget"
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        ordering = ["-period_start", "name"]
        unique_together = ["user", "category", "period_start", "period_end"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "period_start", "period_end"]),
            models.Index(fields=["user", "category", "is_active"]),
            models.Index(fields=["user", "amount_index"]),
        ]

    def __str__(self):
        """Return string representation of the budget."""
        return (
            f"{self.name} - ${self.amount} ({self.period_start} to {self.period_end})"
        )

    def clean(self):
        """Validate the budget."""
        super().clean()

        # Validate amount is positive
        if self.amount is not None and self.amount <= Decimal("0"):
            raise ValidationError("Budget amount must be greater than zero.")

        # Validate period_end is after period_start
        if self.period_start and self.period_end:
            if self.period_end <= self.period_start:
                raise ValidationError("Budget end date must be after start date.")

        # Validate category assignment
        if self.category and self.user:
            # Ensure category belongs to same user
            if self.category.user != self.user:
                raise ValidationError("Category must belong to the same user.")

        # Validate alert thresholds
        if self.warning_threshold is not None and self.warning_threshold < Decimal("0"):
            raise ValidationError("Warning threshold must be non-negative.")

        if self.critical_threshold is not None and self.critical_threshold < Decimal(
            "0"
        ):
            raise ValidationError("Critical threshold must be non-negative.")

        if (
            self.warning_threshold is not None
            and self.critical_threshold is not None
            and self.warning_threshold > self.critical_threshold
        ):
            raise ValidationError(
                "Warning threshold cannot be greater than critical threshold."
            )

        # Check for unique constraint violation manually for better error messages
        if self.user and self.period_start and self.period_end:
            existing_budgets = Budget.objects.filter(
                user=self.user,
                category=self.category,
                period_start=self.period_start,
                period_end=self.period_end,
                is_active=True,
            ).exclude(pk=self.pk)

            if existing_budgets.exists():
                if self.category:
                    raise ValidationError(
                        f"A budget for category '{self.category.name}' "
                        f"already exists for this period."
                    )
                else:
                    raise ValidationError(
                        "An overall budget already exists for this period."
                    )

    def save(self, *args, **kwargs):
        """Save the budget with validation."""
        self.full_clean()

        # Sync amount_index with encrypted amount
        if self.amount is not None:
            self.amount_index = self.amount

        super().save(*args, **kwargs)

    def calculate_spent_amount(self):
        """Calculate the total amount spent against this budget."""
        from apps.expenses.models import Transaction

        # Build the base query for transactions within the budget period
        transaction_filter = Q(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            date__gte=self.period_start,
            date__lte=self.period_end,
            is_active=True,
        )

        # If this budget is category-specific, filter by category
        if self.category:
            transaction_filter &= Q(category=self.category)

        # Get the sum of amount_index (non-encrypted amounts for aggregation)
        spent = Transaction.objects.filter(transaction_filter).aggregate(
            total=Sum("amount_index")
        )["total"] or Decimal("0")

        return spent

    def calculate_remaining_amount(self):
        """Calculate the remaining budget amount."""
        spent = self.calculate_spent_amount()
        return self.amount - spent

    def calculate_utilization_percentage(self):
        """Calculate the percentage of budget utilized."""
        if not self.amount or self.amount == 0:
            return Decimal("0")

        spent = self.calculate_spent_amount()
        percentage = (spent / self.amount) * Decimal("100")
        return percentage.quantize(Decimal("0.01"))  # Round to 2 decimal places

    def is_over_budget(self):
        """Check if the budget has been exceeded."""
        return self.calculate_spent_amount() > self.amount

    @classmethod
    def get_active_budgets_for_user(cls, user):
        """Get all active budgets for a user."""
        return cls.objects.filter(user=user, is_active=True).order_by(
            "-period_start", "name"
        )

    @classmethod
    def get_budgets_for_period(cls, user, start_date, end_date):
        """Get budgets that overlap with a given period."""
        return cls.objects.filter(
            user=user,
            is_active=True,
            period_start__lte=end_date,
            period_end__gte=start_date,
        ).order_by("-period_start", "name")

    @classmethod
    def get_current_budgets(cls, user, current_date=None):
        """Get budgets that are active for the current date."""
        if current_date is None:
            from django.utils import timezone

            current_date = timezone.now().date()

        return cls.objects.filter(
            user=user,
            is_active=True,
            period_start__lte=current_date,
            period_end__gte=current_date,
        ).order_by("name")

    def should_trigger_warning_alert(self):
        """Check if a warning alert should be triggered for this budget."""
        if not self.alert_enabled or not self.warning_threshold:
            return False

        utilization = self.calculate_utilization_percentage()
        return utilization >= self.warning_threshold

    def should_trigger_critical_alert(self):
        """Check if a critical alert should be triggered for this budget."""
        if not self.alert_enabled or not self.critical_threshold:
            return False

        utilization = self.calculate_utilization_percentage()
        return utilization >= self.critical_threshold

    def generate_alerts(self):
        """Generate alerts for this budget if thresholds are crossed."""
        generated_alerts = []

        if not self.alert_enabled:
            return generated_alerts

        current_utilization = self.calculate_utilization_percentage()

        # Check for warning alerts
        if self.should_trigger_warning_alert():
            alert = self._create_alert_if_not_exists("WARNING", current_utilization)
            if alert:
                generated_alerts.append(alert)

        # Check for critical alerts
        if self.should_trigger_critical_alert():
            alert = self._create_alert_if_not_exists("CRITICAL", current_utilization)
            if alert:
                generated_alerts.append(alert)

        return generated_alerts

    def _create_alert_if_not_exists(self, alert_type, current_utilization):
        """Create an alert if one doesn't already exist for this type."""
        # Check if unresolved alert already exists for this type
        existing_alert = BudgetAlert.objects.filter(
            budget=self,
            alert_type=getattr(BudgetAlert, alert_type),
            is_resolved=False,
        ).first()

        if existing_alert:
            return None  # Don't create duplicate alerts

        # Create new alert
        threshold = getattr(self, f"{alert_type.lower()}_threshold")
        if alert_type == "WARNING":
            message = f"Budget '{self.name}' has reached {threshold}% warning threshold"
        else:  # CRITICAL
            message = (
                f"Budget '{self.name}' has reached {threshold}% critical threshold"
            )

        alert = BudgetAlert.objects.create(
            budget=self,
            alert_type=getattr(BudgetAlert, alert_type),
            message=message,
            triggered_at_percentage=current_utilization,
        )

        return alert


class BudgetAlert(models.Model):
    """
    Budget alert model for tracking budget threshold violations.

    Tracks when budgets reach warning or critical thresholds and provides
    a notification system for users to be alerted about their spending.
    """

    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

    ALERT_TYPE_CHOICES = [
        (WARNING, "Warning"),
        (CRITICAL, "Critical"),
    ]

    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name="alerts",
        help_text="Budget this alert is for",
    )

    alert_type = models.CharField(
        max_length=10,
        choices=ALERT_TYPE_CHOICES,
        help_text="Type of alert (WARNING or CRITICAL)",
    )

    message = models.TextField(
        help_text="Alert message describing the threshold violation",
    )

    triggered_at_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Budget utilization percentage when alert was triggered",
    )

    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether this alert has been resolved",
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this alert was resolved",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this alert was created",
    )

    class Meta:
        db_table = "budgets_budgetalert"
        verbose_name = "Budget Alert"
        verbose_name_plural = "Budget Alerts"
        ordering = ["-created_at"]
        unique_together = ["budget", "alert_type", "is_resolved"]
        indexes = [
            models.Index(fields=["budget", "is_resolved"]),
            models.Index(fields=["budget", "alert_type", "is_resolved"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        """Return string representation of the alert."""
        percentage = (
            f" at {self.triggered_at_percentage}%"
            if self.triggered_at_percentage
            else ""
        )
        return f"{self.alert_type} alert for {self.budget.name}{percentage}"

    def mark_as_resolved(self):
        """Mark this alert as resolved."""
        from django.utils import timezone

        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save(update_fields=["is_resolved", "resolved_at"])

    @classmethod
    def get_active_alerts_for_budget(cls, budget):
        """Get active (unresolved) alerts for a specific budget."""
        return cls.objects.filter(budget=budget, is_resolved=False).order_by(
            "-created_at"
        )

    @classmethod
    def get_alerts_for_user(cls, user):
        """Get all alerts for a specific user."""
        return cls.objects.filter(budget__user=user).order_by("-created_at")
