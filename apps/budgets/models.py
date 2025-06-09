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
