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


class BudgetAlertTestCase(TestCase):
    """Test case for Budget alert functionality."""

    def setUp(self):
        """Set up test data."""
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.category1 = CategoryFactory(user=self.user1, name="Groceries")

        # Create test dates
        today = date.today()
        self.start_date = today.replace(day=1)
        self.end_date = today.replace(day=28)

    def test_budget_alert_fields(self):
        """Test that budget has alert-related fields."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("500.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Test Budget",
            alert_enabled=True,
            warning_threshold=Decimal("80.00"),
            critical_threshold=Decimal("100.00"),
        )

        self.assertTrue(budget.alert_enabled)
        self.assertEqual(budget.warning_threshold, Decimal("80.00"))
        self.assertEqual(budget.critical_threshold, Decimal("100.00"))

    def test_alert_threshold_validation(self):
        """Test validation of alert threshold values."""
        # Test negative warning threshold
        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user1,
                category=self.category1,
                amount=Decimal("500.00"),
                period_start=self.start_date,
                period_end=self.end_date,
                name="Invalid Warning Threshold",
                warning_threshold=Decimal("-10.00"),
            )
            budget.full_clean()

        # Test warning threshold greater than critical threshold
        with self.assertRaises(ValidationError):
            budget = Budget(
                user=self.user1,
                category=self.category1,
                amount=Decimal("500.00"),
                period_start=self.start_date,
                period_end=self.end_date,
                name="Invalid Threshold Order",
                warning_threshold=Decimal("120.00"),
                critical_threshold=Decimal("100.00"),
            )
            budget.full_clean()

    def test_should_trigger_warning_alert(self):
        """Test logic for determining if warning alert should be triggered."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Warning Test Budget",
            alert_enabled=True,
            warning_threshold=Decimal("80.00"),
        )

        # Should not trigger warning when under threshold
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("50.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction",
        )
        self.assertFalse(budget.should_trigger_warning_alert())

        # Should trigger warning when at threshold
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("30.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=2),
            description="Test transaction 2",
        )
        self.assertTrue(budget.should_trigger_warning_alert())

    def test_should_trigger_critical_alert(self):
        """Test logic for determining if critical alert should be triggered."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Critical Test Budget",
            alert_enabled=True,
            critical_threshold=Decimal("100.00"),
        )

        # Should not trigger critical when under threshold
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("90.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction",
        )
        self.assertFalse(budget.should_trigger_critical_alert())

        # Should trigger critical when at threshold
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("10.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=2),
            description="Test transaction 2",
        )
        self.assertTrue(budget.should_trigger_critical_alert())

    def test_alert_disabled_budget(self):
        """Test that alerts are not triggered when disabled."""
        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Disabled Alert Budget",
            alert_enabled=False,
            warning_threshold=Decimal("80.00"),
        )

        # Create transaction that would trigger warning
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("90.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction",
        )

        self.assertFalse(budget.should_trigger_warning_alert())
        self.assertFalse(budget.should_trigger_critical_alert())

    def test_generate_alerts_for_budget(self):
        """Test generation of alerts for a budget."""
        from apps.budgets.models import BudgetAlert

        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Alert Generation Budget",
            alert_enabled=True,
            warning_threshold=Decimal("80.00"),
            critical_threshold=Decimal("100.00"),
        )

        # Create transaction that triggers warning
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("85.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction",
        )

        # Generate alerts
        alerts = budget.generate_alerts()

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, BudgetAlert.WARNING)
        self.assertEqual(alerts[0].budget, budget)

    def test_prevent_duplicate_alerts(self):
        """Test that duplicate alerts are not generated for the same threshold."""
        from apps.budgets.models import BudgetAlert

        budget = Budget.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("100.00"),
            period_start=self.start_date,
            period_end=self.end_date,
            name="Duplicate Prevention Budget",
            alert_enabled=True,
            warning_threshold=Decimal("80.00"),
        )

        # Create transaction that triggers warning
        Transaction.objects.create(
            user=self.user1,
            category=self.category1,
            amount=Decimal("85.00"),
            transaction_type=Transaction.EXPENSE,
            date=self.start_date + timedelta(days=1),
            description="Test transaction",
        )

        # Generate alerts first time
        alerts1 = budget.generate_alerts()
        self.assertEqual(len(alerts1), 1)

        # Try to generate again - should not create duplicates
        alerts2 = budget.generate_alerts()
        self.assertEqual(len(alerts2), 0)

        # Verify only one alert exists in database
        total_alerts = BudgetAlert.objects.filter(budget=budget).count()
        self.assertEqual(total_alerts, 1)


class BudgetAlertModelTestCase(TestCase):
    """Test case for BudgetAlert model."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user, name="Test Category")

        today = date.today()
        self.budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            period_start=today.replace(day=1),
            period_end=today.replace(day=28),
            name="Test Budget",
            alert_enabled=True,
            warning_threshold=Decimal("80.00"),
        )

    def test_budget_alert_creation(self):
        """Test basic BudgetAlert creation."""
        from apps.budgets.models import BudgetAlert

        alert = BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.WARNING,
            message="Budget has reached 80% of limit",
            triggered_at_percentage=Decimal("85.00"),
        )

        self.assertEqual(alert.budget, self.budget)
        self.assertEqual(alert.alert_type, BudgetAlert.WARNING)
        self.assertEqual(alert.message, "Budget has reached 80% of limit")
        self.assertEqual(alert.triggered_at_percentage, Decimal("85.00"))
        self.assertFalse(alert.is_resolved)
        self.assertIsNotNone(alert.created_at)

    def test_budget_alert_str_representation(self):
        """Test string representation of BudgetAlert."""
        from apps.budgets.models import BudgetAlert

        alert = BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.CRITICAL,
            message="Budget exceeded",
            triggered_at_percentage=Decimal("105.00"),
        )

        expected = f"CRITICAL alert for {self.budget.name} at 105.00%"
        self.assertEqual(str(alert), expected)

    def test_alert_resolution(self):
        """Test marking alert as resolved."""
        from apps.budgets.models import BudgetAlert

        alert = BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.WARNING,
            message="Test alert",
        )

        self.assertFalse(alert.is_resolved)
        self.assertIsNone(alert.resolved_at)

        alert.mark_as_resolved()

        self.assertTrue(alert.is_resolved)
        self.assertIsNotNone(alert.resolved_at)

    def test_alert_unique_constraint(self):
        """Test that only one unresolved alert per type per budget is allowed."""
        from django.db import IntegrityError

        from apps.budgets.models import BudgetAlert

        # Create first warning alert
        BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.WARNING,
            message="First warning",
        )

        # Try to create another unresolved warning alert for same budget
        with self.assertRaises(IntegrityError):
            BudgetAlert.objects.create(
                budget=self.budget,
                alert_type=BudgetAlert.WARNING,
                message="Second warning",
            )

    def test_multiple_alert_types_allowed(self):
        """Test that different alert types can coexist for same budget."""
        from apps.budgets.models import BudgetAlert

        warning_alert = BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.WARNING,
            message="Warning alert",
        )

        critical_alert = BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.CRITICAL,
            message="Critical alert",
        )

        self.assertNotEqual(warning_alert.alert_type, critical_alert.alert_type)
        self.assertEqual(BudgetAlert.objects.filter(budget=self.budget).count(), 2)

    def test_get_active_alerts_for_budget(self):
        """Test getting active (unresolved) alerts for a budget."""
        from apps.budgets.models import BudgetAlert

        # Create active alert
        active_alert = BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.WARNING,
            message="Active alert",
        )

        # Create resolved alert
        resolved_alert = BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.CRITICAL,
            message="Resolved alert",
            is_resolved=True,
        )

        active_alerts = BudgetAlert.get_active_alerts_for_budget(self.budget)

        self.assertEqual(active_alerts.count(), 1)
        self.assertIn(active_alert, active_alerts)
        self.assertNotIn(resolved_alert, active_alerts)

    def test_get_alerts_for_user(self):
        """Test getting alerts for a specific user."""
        from apps.budgets.models import BudgetAlert

        # Create alert for user1
        alert1 = BudgetAlert.objects.create(
            budget=self.budget,
            alert_type=BudgetAlert.WARNING,
            message="User1 alert",
        )

        # Create budget and alert for different user
        user2 = UserFactory()
        category2 = CategoryFactory(user=user2, name="User2 Category")
        budget2 = Budget.objects.create(
            user=user2,
            category=category2,
            amount=Decimal("200.00"),
            period_start=date.today().replace(day=1),
            period_end=date.today().replace(day=28),
            name="User2 Budget",
        )
        BudgetAlert.objects.create(
            budget=budget2,
            alert_type=BudgetAlert.CRITICAL,
            message="User2 alert",
        )

        user_alerts = BudgetAlert.get_alerts_for_user(self.user)

        self.assertEqual(user_alerts.count(), 1)
        self.assertIn(alert1, user_alerts)
