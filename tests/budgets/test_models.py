"""
Tests for budget models.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.budgets.models import Budget
from apps.expenses.models import Transaction
from tests.factories import CategoryFactory, UserFactory

User = get_user_model()


class BudgetModelTestCase(TestCase):
    """Test case for Budget model."""

    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.category1 = CategoryFactory(user=self.user1, name="Groceries")
        self.category2 = CategoryFactory(user=self.user2, name="Transport")

        # Create test dates (use previous month to ensure they're in the past)
        today = date.today()
        if today.month == 1:
            # Handle January (previous month is December of previous year)
            self.start_date = date(today.year - 1, 12, 1)
            self.end_date = date(today.year - 1, 12, 28)
        else:
            # Previous month of same year
            self.start_date = date(today.year, today.month - 1, 1)
            self.end_date = date(today.year, today.month - 1, 28)

    def test_budget_creation(self):
        """Test basic budget creation."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Monthly Groceries",
        )

        self.assertEqual(budget.user, self.user1)
        self.assertEqual(budget.category, self.category1)
        self.assertEqual(budget.amount, Decimal("500.00"))
        self.assertEqual(budget.amount_index, Decimal("500.00"))
        self.assertEqual(budget.period_start, self.start_date)
        self.assertEqual(budget.period_end, self.end_date)
        self.assertEqual(budget.name, "Monthly Groceries")
        self.assertTrue(budget.is_active)
        self.assertIsNotNone(budget.created_at)
        self.assertIsNotNone(budget.updated_at)

    def test_budget_str_representation(self):
        """Test string representation of budget."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Monthly Groceries",
        )
        expected = (
            f"Monthly Groceries - ${budget.amount} "
            f"({self.start_date} to {self.end_date})"
        )
        self.assertEqual(str(budget), expected)

    def test_budget_without_category(self):
        """Test budget creation without category (overall budget)."""
        budget = Budget.objects.create(
            user=self.user1,
            amount=Decimal("2000.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Total Monthly Budget",
        )

        self.assertEqual(budget.user, self.user1)
        self.assertIsNone(budget.category)
        self.assertEqual(budget.amount, Decimal("2000.00"))

    def test_user_specific_budgets(self):
        """Test that budgets are user-specific."""
        budget1 = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("300.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="User1 Budget",
        )
        budget2 = Budget.objects.create(
            user=self.user2,
            category=self.category2,
            amount=Decimal("400.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="User2 Budget",
        )

        self.assertNotEqual(budget1.user, budget2.user)
        self.assertEqual(Budget.objects.filter(user=self.user1).count(), 1)
        self.assertEqual(Budget.objects.filter(user=self.user2).count(), 1)

    def test_budget_validation_positive_amount(self):
        """Test that budget amount must be positive."""
        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user1,
                category=self.category1,
                amount=Decimal("-100.00"),
                period_start=self.start_date,
                period_end=self.end_date,
                name="Invalid Budget",
            )
            budget.full_clean()

        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user1,
                category=self.category1,
                amount=Decimal("0.00"),
                period_start=self.start_date,
                period_end=self.end_date,
                name="Zero Budget",
            )
            budget.full_clean()

    def test_budget_validation_date_range(self):
        """Test that period_end must be after period_start."""
        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user1,
                category=self.category1,
                amount=Decimal("500.00"),
                period_start=self.end_date,
                period_end=self.start_date,  # End before start
                name="Invalid Date Range",
            )
            budget.full_clean()

    def test_budget_validation_category_user_match(self):
        """Test that category must belong to the same user as the budget."""
        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user1,
                category=self.category2,  # Belongs to user2
                amount=Decimal("500.00"),
                period_start=self.start_date,
                period_end=self.end_date,
                name="Mismatched User Budget",
            )
            budget.full_clean()

    def test_budget_unique_constraint(self):
        """Test unique constraint on user, category, period_start, period_end."""
        # Create first budget
        Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="First Budget",
        )

        # Try to create duplicate budget
        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user1,
                category=self.category1,
                amount=Decimal("600.00"),  # Different amount
                period_start=self.start_date,
                period_end=self.end_date,
                name="Duplicate Budget",
            )
            budget.full_clean()

    def test_calculate_spent_amount_with_transactions(self):
        """Test calculation of spent amount with transactions."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Groceries Budget",
        )

        # Create transactions within the budget period
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction 1",
        )
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("75.50"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=10),
            description="Test transaction 2",
        )

        # Create transaction outside the period (should not count)
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("50.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.end_date + timedelta(days=1),
            description="Test transaction outside period",
        )

        spent = budget.calculate_spent_amount()
        self.assertEqual(spent, Decimal("175.50"))

    def test_calculate_spent_amount_no_category(self):
        """Test calculation for budget without category (overall budget)."""
        budget = Budget.objects.create(
            user=self.user1,
            amount=Decimal("2000.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Total Budget",
        )

        # Create transactions in different categories
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction 1",
        )

        # Create another category for user1
        category2 = CategoryFactory(user=self.user1, name="Entertainment")
        Transaction.objects.create(
            user=self.user1,
            category=category2,
            amount=Decimal("80.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=5),
            description="Test transaction 2",
        )

        # Should include all expenses for the user
        spent = budget.calculate_spent_amount()
        self.assertEqual(spent, Decimal("180.00"))

    def test_calculate_spent_amount_exclude_income(self):
        """Test that income transactions are excluded from spent calculations."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Groceries Budget",
        )

        # Create expense
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test expense",
        )

        # Create income (should be excluded)
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("50.00"),
            transaction_type=Transaction.INCOME,
            date=self.start_date + timedelta(days=2),
            description="Test income",
        )

        spent = budget.calculate_spent_amount()
        self.assertEqual(spent, Decimal("100.00"))

    def test_calculate_remaining_amount(self):
        """Test calculation of remaining budget amount."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Groceries Budget",
        )

        # Create transaction
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("150.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction",
        )

        remaining = budget.calculate_remaining_amount()
        self.assertEqual(remaining, Decimal("350.00"))

    def test_calculate_utilization_percentage(self):
        """Test calculation of budget utilization percentage."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Groceries Budget",
        )

        # Create transaction for 30% of budget
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("150.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction",
        )

        utilization = budget.calculate_utilization_percentage()
        self.assertEqual(utilization, Decimal("30.00"))

    def test_calculate_utilization_percentage_over_budget(self):
        """Test utilization percentage when over budget."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Small Budget",
        )

        # Spend more than budget
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("150.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Over budget transaction",
        )

        utilization = budget.calculate_utilization_percentage()
        self.assertEqual(utilization, Decimal("150.00"))

    def test_is_over_budget(self):
        """Test checking if budget is exceeded."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Small Budget",
        )

        # Under budget
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("50.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Under budget transaction",
        )
        self.assertFalse(budget.is_over_budget())

        # Over budget
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("75.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=2),
            description="Over budget transaction",
        )
        self.assertTrue(budget.is_over_budget())

    def test_get_active_budgets_for_user(self):
        """Test class method to get active budgets for a user."""
        # Create active budgets
        budget1 = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Budget 1",
        )
        budget2 = Budget.objects.create(
            user=self.user1,
            amount=Decimal("1000.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Budget 2",
        )

        # Create inactive budget with different category
        inactive_category = CategoryFactory(user=self.user1, name="Inactive Category")
        Budget.objects.create(
            user=self.user1,
            category=inactive_category,
            amount=Decimal("300.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Inactive Budget",
            is_active=False,
        )

        # Create budget for different user
        Budget.objects.create(
            user=self.user2,
            category=self.category2,
            amount=Decimal("200.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Other User Budget",
        )

        active_budgets = Budget.get_active_budgets_for_user(self.user1)
        self.assertEqual(active_budgets.count(), 2)
        self.assertIn(budget1, active_budgets)
        self.assertIn(budget2, active_budgets)

    def test_get_budgets_for_period(self):
        """Test class method to get budgets for a specific period."""
        # Budget that overlaps with test period
        budget1 = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Overlapping Budget",
        )

        # Budget outside test period
        Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("300.00"),
            period_start=self.end_date + timedelta(days=1),
            period_end=self.end_date + timedelta(days=30),
            name="Future Budget",
        )

        budgets = Budget.get_budgets_for_period(
            self.user1, self.start_date, self.end_date
        )
        self.assertEqual(budgets.count(), 1)
        self.assertIn(budget1, budgets)

    def test_amount_index_sync(self):
        """Test that amount_index is synced with encrypted amount on save."""
        budget = Budget(
            user=self.user1,
            category=self.category1,
            amount=Decimal("750.25"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Sync Test Budget",
        )
        budget.save()

        # Refresh from database
        budget.refresh_from_db()
        self.assertEqual(budget.amount_index, budget.amount)
        self.assertEqual(budget.amount_index, Decimal("750.25"))
