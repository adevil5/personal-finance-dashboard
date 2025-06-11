import re
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.security.fields import (
    EncryptedCharField,
    EncryptedDecimalField,
    EncryptedTextField,
)
from apps.core.security.validators import validate_receipt_file

User = get_user_model()


def validate_hex_color(value):
    """Validate that the value is a valid hex color."""
    if value and not re.match(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", value):
        raise ValidationError(f"{value} is not a valid hex color")


class Category(models.Model):
    """
    Category model for organizing expenses.

    Supports hierarchical structure with parent-child relationships
    and user-specific categories for data isolation.
    """

    name = models.CharField(max_length=100, help_text="Category name")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="categories",
        help_text="User this category belongs to",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent category for hierarchical structure",
    )

    color = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        validators=[validate_hex_color],
        help_text="Category color in hex format (e.g., #FF0000)",
    )

    icon = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Icon identifier for the category",
    )

    is_active = models.BooleanField(
        default=True, help_text="Whether this category is active (soft delete)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When this category was created"
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text="When this category was last updated"
    )

    class Meta:
        db_table = "expenses_category"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]
        unique_together = ["user", "name", "parent"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "parent"]),
        ]

    def __str__(self):
        """Return string representation of the category."""
        return self.name

    def clean(self):
        """Validate the category."""
        super().clean()

        # Prevent self as parent
        if self.parent == self:
            raise ValidationError("A category cannot be its own parent.")

        # Prevent circular references
        if self.parent and self._would_create_cycle():
            raise ValidationError(
                "This parent assignment would create a circular reference."
            )

        # Ensure parent belongs to same user
        if self.parent and self.parent.user != self.user:
            raise ValidationError("Parent category must belong to the same user.")

    def _would_create_cycle(self):
        """Check if setting the current parent would create a circular reference."""
        current = self.parent
        while current:
            if current == self:
                return True
            current = current.parent
        return False

    def get_level(self):
        """Get the level of this category in the hierarchy (0 for root)."""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level

    def get_descendants(self):
        """Get all descendants of this category."""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_ancestors(self):
        """Get all ancestors of this category."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    @classmethod
    def get_root_categories(cls, user):
        """Get all root categories (no parent) for a user."""
        return cls.objects.filter(user=user, parent=None, is_active=True)

    @classmethod
    def get_category_tree(cls, user):
        """Get all categories for a user ordered for tree display."""
        return cls.objects.filter(user=user, is_active=True).order_by("name")

    @classmethod
    def create_default_categories(cls, user):
        """Create default categories for a user."""
        from .default_categories import DEFAULT_CATEGORIES

        # Check if user already has categories to avoid duplicates
        if cls.objects.filter(user=user).exists():
            return

        for category_data in DEFAULT_CATEGORIES:
            # Create parent category
            parent_category = cls.objects.create(
                name=category_data["name"],
                user=user,
                color=category_data["color"],
                icon=category_data["icon"],
            )

            # Create child categories
            for child_data in category_data["children"]:
                cls.objects.create(
                    name=child_data["name"],
                    user=user,
                    parent=parent_category,
                    color=child_data["color"],
                    icon=child_data["icon"],
                )


def upload_receipt_to(instance, filename):
    """Generate upload path for receipt files."""
    return f"receipts/{instance.user.id}/{filename}"


class Transaction(models.Model):
    """
    Transaction model for tracking financial transactions.

    Supports expense, income, and transfer transaction types with encrypted PII fields
    for secure storage of financial information. Also supports recurring transactions
    with various frequency options.
    """

    # Transaction type choices
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"

    TRANSACTION_TYPE_CHOICES = [
        (EXPENSE, "Expense"),
        (INCOME, "Income"),
        (TRANSFER, "Transfer"),
    ]

    # Recurring frequency choices
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

    RECURRING_FREQUENCY_CHOICES = [
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
        (YEARLY, "Yearly"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transactions",
        help_text="User this transaction belongs to",
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE_CHOICES,
        help_text="Type of transaction",
    )

    amount = EncryptedDecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount (encrypted)",
    )

    amount_index = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Transaction amount for filtering/sorting (non-encrypted)",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        help_text="Category for this transaction (required for expenses)",
    )

    description = models.CharField(
        max_length=255,
        help_text="Transaction description",
    )

    notes = EncryptedTextField(
        blank=True,
        null=True,
        help_text="Additional notes about the transaction (encrypted)",
    )

    merchant = EncryptedCharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Merchant or payee name (encrypted)",
    )

    date = models.DateField(
        help_text="Transaction date",
    )

    receipt = models.FileField(
        upload_to=upload_receipt_to,
        blank=True,
        null=True,
        validators=[validate_receipt_file],
        help_text="Receipt or supporting document (images and PDFs only, max 10MB)",
    )

    # Recurring transaction fields
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this transaction repeats automatically",
    )

    recurring_frequency = models.CharField(
        max_length=10,
        choices=RECURRING_FREQUENCY_CHOICES,
        blank=True,
        null=True,
        help_text="How often the transaction repeats",
    )

    recurring_interval = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Interval for recurring frequency (e.g., every 2 weeks)",
    )

    recurring_start_date = models.DateField(
        blank=True,
        null=True,
        help_text="When the recurring pattern starts",
    )

    recurring_end_date = models.DateField(
        blank=True,
        null=True,
        help_text="When the recurring pattern ends (optional)",
    )

    next_occurrence = models.DateField(
        blank=True,
        null=True,
        help_text="When the next transaction should be generated",
    )

    parent_transaction = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="recurring_children",
        help_text="Parent transaction for recurring series",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this transaction is active (soft delete)",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this transaction was created",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this transaction was last updated",
    )

    class Meta:
        db_table = "expenses_transaction"
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ["-date", "-created_at"]  # Newest first
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["user", "transaction_type", "is_active"]),
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "category", "is_active"]),
            models.Index(
                fields=["user", "amount_index"]
            ),  # For amount filtering/sorting
            models.Index(fields=["is_recurring", "next_occurrence"]),
            models.Index(fields=["user", "is_recurring"]),
            models.Index(fields=["parent_transaction"]),
        ]

    def __str__(self):
        """Return string representation of the transaction."""
        return (
            f"{self.get_transaction_type_display()} - "
            f"${self.amount} - {self.description}"
        )

    def clean(self):
        """Validate the transaction."""
        super().clean()

        # Validate amount is positive
        if self.amount is not None and self.amount <= Decimal("0"):
            raise ValidationError("Amount must be greater than zero.")

        # Validate date is not in the future (except for generated recurring
        # transactions)
        if (
            self.date
            and self.date > date.today()
            and not (self.parent_transaction and not self.is_recurring)
        ):
            raise ValidationError("Transaction date cannot be in the future.")

        # Validate category assignment
        if self.category and self.user:
            # Ensure category belongs to same user
            if self.category.user != self.user:
                raise ValidationError("Category must belong to the same user.")

        # Validate expense transactions require a category
        if self.transaction_type == self.EXPENSE and not self.category:
            raise ValidationError("Expense transactions must have a category.")

        # Validate recurring transaction fields
        if self.is_recurring:
            if not self.recurring_frequency:
                raise ValidationError("Recurring transactions must have a frequency.")

            if not self.recurring_interval or self.recurring_interval <= 0:
                raise ValidationError(
                    "Recurring transactions must have a positive interval."
                )

            if not self.recurring_start_date:
                raise ValidationError("Recurring transactions must have a start date.")

            if (
                self.recurring_end_date
                and self.recurring_end_date <= self.recurring_start_date
            ):
                raise ValidationError("Recurring end date must be after start date.")

    def save(self, *args, **kwargs):
        """Save the transaction with validation."""
        self.full_clean()

        # Sync amount_index with encrypted amount
        if self.amount is not None:
            self.amount_index = self.amount

        # Calculate next_occurrence for recurring transactions
        if self.is_recurring and not self.next_occurrence:
            self.next_occurrence = self.calculate_next_occurrence()

        # Clear next_occurrence for non-recurring transactions
        if not self.is_recurring:
            self.next_occurrence = None

        super().save(*args, **kwargs)

    def calculate_next_occurrence(self):
        """Calculate the next occurrence date for recurring transactions."""
        if not self.is_recurring or not self.recurring_start_date:
            return None

        from datetime import timedelta

        from dateutil.relativedelta import relativedelta

        base_date = self.recurring_start_date
        interval = self.recurring_interval or 1

        if self.recurring_frequency == self.DAILY:
            next_date = base_date + timedelta(days=interval)
        elif self.recurring_frequency == self.WEEKLY:
            next_date = base_date + timedelta(weeks=interval)
        elif self.recurring_frequency == self.MONTHLY:
            next_date = base_date + relativedelta(months=interval)
        elif self.recurring_frequency == self.YEARLY:
            next_date = base_date + relativedelta(years=interval)
        else:
            return None

        # Handle end date
        if self.recurring_end_date and next_date > self.recurring_end_date:
            return None

        return next_date

    def generate_next_transaction(self):
        """Generate the next transaction in the recurring series."""
        if not self.is_recurring or not self.next_occurrence:
            return None

        from datetime import timedelta

        from dateutil.relativedelta import relativedelta

        # Create new transaction based on this one
        new_transaction = Transaction(
            user=self.user,
            transaction_type=self.transaction_type,
            amount=self.amount,
            amount_index=self.amount,  # Sync amount_index
            category=self.category,
            description=self.description,
            notes=self.notes,
            merchant=self.merchant,
            date=self.next_occurrence,
            is_recurring=False,  # Generated transactions are not recurring
            parent_transaction=self,
        )

        # Copy receipt if present (same file reference)
        if self.receipt:
            new_transaction.receipt = self.receipt

        # Save the new transaction
        new_transaction.save()

        # Update next occurrence for this recurring transaction
        interval = self.recurring_interval or 1

        if self.recurring_frequency == self.DAILY:
            next_date = self.next_occurrence + timedelta(days=interval)
        elif self.recurring_frequency == self.WEEKLY:
            next_date = self.next_occurrence + timedelta(weeks=interval)
        elif self.recurring_frequency == self.MONTHLY:
            next_date = self.next_occurrence + relativedelta(months=interval)
        elif self.recurring_frequency == self.YEARLY:
            next_date = self.next_occurrence + relativedelta(years=interval)
        else:
            next_date = None

        # Check if we've reached the end date
        if (
            self.recurring_end_date
            and next_date
            and next_date > self.recurring_end_date
        ):
            self.next_occurrence = None
        else:
            self.next_occurrence = next_date

        # Save updated next occurrence (use update to avoid triggering save logic)
        Transaction.objects.filter(id=self.id).update(
            next_occurrence=self.next_occurrence
        )

        return new_transaction

    def stop_recurring(self):
        """Stop this recurring transaction."""
        self.is_recurring = False
        self.next_occurrence = None
        self.save()
