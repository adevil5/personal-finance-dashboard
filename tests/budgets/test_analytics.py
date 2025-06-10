"""
Tests for budget analytics functionality.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.expenses.models import Transaction
from tests.factories import BudgetFactory, CategoryFactory, TransactionFactory

User = get_user_model()


@pytest.mark.django_db
class TestBudgetAnalytics:
    """Test budget analytics functionality."""

    def setup_method(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        # Create categories
        self.food_category = CategoryFactory(user=self.user, name="Food")
        self.transport_category = CategoryFactory(user=self.user, name="Transport")
        self.entertainment_category = CategoryFactory(
            user=self.user, name="Entertainment"
        )

        # Create date ranges for different periods (use previous month to ensure dates are in the past)  # noqa: E501
        today = date.today()

        # Use previous month as "current" to avoid future date issues
        if today.month == 1:
            self.current_month_start = date(today.year - 1, 12, 1)
            self.current_month_end = date(today.year - 1, 12, 28)
        else:
            self.current_month_start = date(today.year, today.month - 1, 1)
            self.current_month_end = date(today.year, today.month - 1, 28)

        # Previous month (2 months ago)
        self.prev_month_end = self.current_month_start - timedelta(days=1)
        self.prev_month_start = self.prev_month_end.replace(day=1)

        # Two months ago
        self.two_months_ago_end = self.prev_month_start - timedelta(days=1)
        self.two_months_ago_start = self.two_months_ago_end.replace(day=1)

    def test_budget_performance_metrics_basic(self):
        """Test basic budget performance metrics calculation."""
        # Create current month budget
        BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Create transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=self.current_month_start + timedelta(days=5),
        )
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            date=self.current_month_start + timedelta(days=10),
        )

        # Test calculated metrics
        assert budget.calculate_spent_amount() == Decimal("250.00")
        assert budget.calculate_remaining_amount() == Decimal("250.00")
        assert budget.calculate_utilization_percentage() == Decimal("50.00")
        assert not budget.is_over_budget()

    def test_budget_performance_metrics_over_budget(self):
        """Test performance metrics when budget is exceeded."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Small Budget",
            amount=Decimal("100.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Exceed budget
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        assert budget.calculate_spent_amount() == Decimal("150.00")
        assert budget.calculate_remaining_amount() == Decimal("-50.00")
        assert budget.calculate_utilization_percentage() == Decimal("150.00")
        assert budget.is_over_budget()

    def test_budget_utilization_percentage_precision(self):
        """Test budget utilization percentage calculation precision."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Precision Test Budget",
            amount=Decimal("333.33"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Spend 1/3 of budget
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("111.11"),
            date=self.current_month_start + timedelta(days=5),
        )

        utilization = budget.calculate_utilization_percentage()
        assert utilization == Decimal("33.33")  # Should be rounded to 2 decimal places

    def test_multi_period_budget_comparison(self):
        """Test budget performance comparison across multiple periods."""
        # Create budgets for different periods
        BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Current Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Previous Food Budget",
            amount=Decimal("450.00"),
            period_start=self.prev_month_start,
            period_end=self.prev_month_end,
        )

        # Add transactions for current month
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("300.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        # Add transactions for previous month
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("400.00"),
            date=self.prev_month_start + timedelta(days=5),
        )

        # Test current budget metrics
        assert current_budget.calculate_utilization_percentage() == Decimal("60.00")
        assert not current_budget.is_over_budget()

        # Test previous budget metrics
        assert prev_budget.calculate_utilization_percentage() == Decimal("88.89")
        assert not prev_budget.is_over_budget()

    def test_category_based_budget_analytics(self):
        """Test analytics for category-specific budgets."""
        # Create budgets for different categories
        BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("400.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        BudgetFactory(
            user=self.user,
            category=self.transport_category,
            name="Transport Budget",
            amount=Decimal("200.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add category-specific transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        # Test category isolation
        assert food_budget.calculate_spent_amount() == Decimal("200.00")
        assert food_budget.calculate_utilization_percentage() == Decimal("50.00")

        assert transport_budget.calculate_spent_amount() == Decimal("150.00")
        assert transport_budget.calculate_utilization_percentage() == Decimal("75.00")

    def test_overall_budget_analytics(self):
        """Test analytics for overall budgets (no category)."""
        # Create overall budget
        overall_budget = BudgetFactory(
            user=self.user,
            category=None,  # Overall budget
            name="Overall Monthly Budget",
            amount=Decimal("1000.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transactions across different categories
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        TransactionFactory(
            user=self.user,
            category=self.entertainment_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        # Should include all expenses for the user
        assert overall_budget.calculate_spent_amount() == Decimal("450.00")
        assert overall_budget.calculate_utilization_percentage() == Decimal("45.00")

    def test_budget_analytics_exclude_income(self):
        """Test that budget analytics exclude income transactions."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add expense transaction
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        # Add income transaction (should be excluded)
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.INCOME,
            amount=Decimal("100.00"),
            date=self.current_month_start + timedelta(days=10),
        )

        # Should only count expense
        assert budget.calculate_spent_amount() == Decimal("200.00")
        assert budget.calculate_utilization_percentage() == Decimal("40.00")

    def test_budget_analytics_period_boundaries(self):
        """Test that budget analytics respect period boundaries."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Transaction within period
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        # Transaction before period (should be excluded)
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            date=self.current_month_start - timedelta(days=1),
        )

        # Transaction after period (should be excluded)
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=self.current_month_end + timedelta(days=1),
        )

        # Should only count transaction within period
        assert budget.calculate_spent_amount() == Decimal("200.00")
        assert budget.calculate_utilization_percentage() == Decimal("40.00")

    def test_budget_analytics_user_isolation(self):
        """Test that budget analytics are isolated per user."""
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpass123",
        )
        other_category = CategoryFactory(user=other_user, name="Other Food")

        # Create budget for current user
        user_budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="User Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transaction for current user
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        # Add transaction for other user (should not affect current user's budget)
        TransactionFactory(
            user=other_user,
            category=other_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("300.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        # Current user's budget should only count their own transactions
        assert user_budget.calculate_spent_amount() == Decimal("200.00")
        assert user_budget.calculate_utilization_percentage() == Decimal("40.00")

    def test_budget_analytics_with_inactive_transactions(self):
        """Test that budget analytics exclude inactive transactions."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add active transaction
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        # Add inactive transaction (should be excluded)
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=self.current_month_start + timedelta(days=10),
            is_active=False,
        )

        # Should only count active transaction
        assert budget.calculate_spent_amount() == Decimal("200.00")
        assert budget.calculate_utilization_percentage() == Decimal("40.00")

    def test_zero_amount_budget_analytics(self):
        """Test analytics behavior with zero amount budget."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Zero Budget",
            amount=Decimal("0.01"),  # Minimum valid amount
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add small transaction
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("0.01"),
            date=self.current_month_start + timedelta(days=5),
        )

        assert budget.calculate_spent_amount() == Decimal("0.01")
        assert budget.calculate_utilization_percentage() == Decimal("100.00")
        assert not budget.is_over_budget()  # Exactly at budget

        # Add another cent to go over
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("0.01"),
            date=self.current_month_start + timedelta(days=6),
        )

        assert budget.calculate_spent_amount() == Decimal("0.02")
        assert budget.calculate_utilization_percentage() == Decimal("200.00")
        assert budget.is_over_budget()

    def test_large_amount_budget_analytics(self):
        """Test analytics with large budget amounts."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Large Budget",
            amount=Decimal("99999999.99"),  # Max supported amount
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add large transaction
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("12345678.90"),
            date=self.current_month_start + timedelta(days=5),
        )

        assert budget.calculate_spent_amount() == Decimal("12345678.90")
        utilization = budget.calculate_utilization_percentage()
        expected_utilization = (
            Decimal("12345678.90") / Decimal("99999999.99") * Decimal("100")
        ).quantize(Decimal("0.01"))
        assert utilization == expected_utilization
        assert not budget.is_over_budget()


@pytest.mark.django_db
class TestBudgetAnalyticsAPI:
    """Test budget analytics API endpoints."""

    def setup_method(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        # Create categories
        self.food_category = CategoryFactory(user=self.user, name="Food")
        self.transport_category = CategoryFactory(user=self.user, name="Transport")

        # Create date ranges (use previous month to ensure dates are in the past)
        today = date.today()
        if today.month == 1:
            self.current_month_start = date(today.year - 1, 12, 1)
            self.current_month_end = date(today.year - 1, 12, 28)
        else:
            self.current_month_start = date(today.year, today.month - 1, 1)
            self.current_month_end = date(today.year, today.month - 1, 28)

    def test_budget_statistics_endpoint_basic(self):
        """Test basic budget statistics endpoint functionality."""
        # Create budgets
        BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        transport_budget = BudgetFactory(
            user=self.user,
            category=self.transport_category,
            name="Transport Budget",
            amount=Decimal("200.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("300.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("180.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-statistics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check required fields
        assert "total_budget" in data
        assert "total_spent" in data
        assert "total_remaining" in data
        assert "overall_utilization_percentage" in data
        assert "budget_count" in data
        assert "over_budget_count" in data

        # Check values
        assert Decimal(data["total_budget"]) == Decimal("700.00")
        assert Decimal(data["total_spent"]) == Decimal("480.00")
        assert Decimal(data["total_remaining"]) == Decimal("220.00")
        assert Decimal(data["overall_utilization_percentage"]) == Decimal("68.57")
        assert data["budget_count"] == 2
        assert data["over_budget_count"] == 0

    def test_budget_statistics_with_over_budget(self):
        """Test statistics calculation when some budgets are over limit."""
        # Create budget that will be exceeded
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Small Budget",
            amount=Decimal("100.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Exceed the budget
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-statistics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert Decimal(data["total_budget"]) == Decimal("100.00")
        assert Decimal(data["total_spent"]) == Decimal("150.00")
        assert Decimal(data["total_remaining"]) == Decimal("-50.00")
        assert Decimal(data["overall_utilization_percentage"]) == Decimal("150.00")
        assert data["budget_count"] == 1
        assert data["over_budget_count"] == 1

    def test_budget_statistics_with_period_filter(self):
        """Test statistics endpoint with period filtering."""
        # Create budget for current month
        current_budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Current Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Create budget for previous month
        prev_month_end = self.current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        prev_budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Previous Budget",
            amount=Decimal("300.00"),
            period_start=prev_month_start,
            period_end=prev_month_end,
        )

        # Add transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-statistics")

        # Filter by current month
        response = self.client.get(
            url,
            {
                "period_start": str(self.current_month_start),
                "period_end": str(self.current_month_end),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Should only include current month budget
        assert Decimal(data["total_budget"]) == Decimal("500.00")
        assert data["budget_count"] == 1
        assert data["period_start"] == str(self.current_month_start)
        assert data["period_end"] == str(self.current_month_end)

    def test_budget_statistics_empty_result(self):
        """Test statistics endpoint with no budgets."""
        url = reverse("api:budget-statistics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert Decimal(data["total_budget"]) == Decimal("0")
        assert Decimal(data["total_spent"]) == Decimal("0")
        assert Decimal(data["total_remaining"]) == Decimal("0")
        assert Decimal(data["overall_utilization_percentage"]) == Decimal("0")
        assert data["budget_count"] == 0
        assert data["over_budget_count"] == 0

    def test_budget_list_includes_analytics_fields(self):
        """Test that budget list endpoint includes analytics fields."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transaction
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        budget_data = response.data["results"][0]

        # Check analytics fields are included
        assert "spent_amount" in budget_data
        assert "remaining_amount" in budget_data
        assert "utilization_percentage" in budget_data
        assert "is_over_budget" in budget_data

        # Check values
        assert Decimal(budget_data["spent_amount"]) == Decimal("200.00")
        assert Decimal(budget_data["remaining_amount"]) == Decimal("300.00")
        assert Decimal(budget_data["utilization_percentage"]) == Decimal("40.00")
        assert budget_data["is_over_budget"] is False

    def test_budget_detail_includes_analytics_fields(self):
        """Test that budget detail endpoint includes analytics fields."""
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transaction
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("350.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-detail", kwargs={"pk": budget.pk})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        budget_data = response.data

        # Check analytics fields
        assert Decimal(budget_data["spent_amount"]) == Decimal("350.00")
        assert Decimal(budget_data["remaining_amount"]) == Decimal("150.00")
        assert Decimal(budget_data["utilization_percentage"]) == Decimal("70.00")
        assert budget_data["is_over_budget"] is False


@pytest.mark.django_db
class TestBudgetAnalyticsEndpoints:
    """Test enhanced budget analytics endpoints."""

    def setup_method(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        # Create categories
        self.food_category = CategoryFactory(user=self.user, name="Food")
        self.transport_category = CategoryFactory(user=self.user, name="Transport")

        # Create date ranges
        today = date.today()
        self.current_month_start = today.replace(day=1)
        self.current_month_end = (
            self.current_month_start + timedelta(days=32)
        ).replace(day=1) - timedelta(days=1)

    def test_budget_analytics_endpoint_basic(self):
        """Test basic analytics endpoint functionality."""
        # Create budget
        budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transaction
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("300.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-analytics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check required fields
        assert "current_period" in data
        current = data["current_period"]
        assert Decimal(current["total_budget"]) == Decimal("500.00")
        assert Decimal(current["total_spent"]) == Decimal("300.00")
        assert Decimal(current["overall_utilization_percentage"]) == Decimal("60.00")

    def test_budget_analytics_with_previous_comparison(self):
        """Test analytics endpoint with previous period comparison."""
        # Create current period budget
        current_budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Current Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Create previous period budget
        prev_month_end = self.current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        prev_budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Previous Food Budget",
            amount=Decimal("400.00"),
            period_start=prev_month_start,
            period_end=prev_month_end,
        )

        # Add transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("300.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=prev_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-analytics")
        response = self.client.get(
            url,
            {
                "period_start": str(self.current_month_start),
                "period_end": str(self.current_month_end),
                "compare_previous": "true",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check structure
        assert "current_period" in data
        assert "previous_period" in data
        assert "comparison" in data

        # Check comparison data
        comparison = data["comparison"]
        assert "budget_change" in comparison
        assert "spending_change" in comparison
        assert "utilization_change" in comparison

    def test_budget_analytics_with_category_breakdown(self):
        """Test analytics endpoint with category breakdown."""
        # Create budgets for different categories
        food_budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("400.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        transport_budget = BudgetFactory(
            user=self.user,
            category=self.transport_category,
            name="Transport Budget",
            amount=Decimal("200.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-analytics")
        response = self.client.get(url, {"category_breakdown": "true"})

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check category breakdown
        assert "category_breakdown" in data
        breakdown = data["category_breakdown"]
        assert len(breakdown) == 2

        # Check category data
        category_names = [item["category"] for item in breakdown]
        assert "Food" in category_names
        assert "Transport" in category_names

    def test_budget_performance_endpoint(self):
        """Test budget performance endpoint."""
        # Create budgets with different performance levels
        BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Excellent Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        BudgetFactory(
            user=self.user,
            category=self.transport_category,
            name="Over Budget",
            amount=Decimal("100.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("200.00"),  # 40% utilization (excellent)
            date=self.current_month_start + timedelta(days=5),
        )

        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),  # 150% utilization (over budget)
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-performance")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check required fields
        assert "total_budgets" in data
        assert "performance_summary" in data
        assert "performance_details" in data
        assert "average_utilization" in data
        assert "best_performers" in data
        assert "worst_performers" in data

        # Check performance summary
        summary = data["performance_summary"]
        assert summary["excellent"] == 1
        assert summary["over_budget"] == 1

        # Check performance details
        details = data["performance_details"]
        assert len(details) == 2

        # Check best/worst performers
        assert len(data["best_performers"]) <= 3
        assert len(data["worst_performers"]) <= 3

    def test_budget_trends_endpoint(self):
        """Test budget trends endpoint."""
        # Create budgets for current month
        current_budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Current Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Add transaction
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("300.00"),
            date=self.current_month_start + timedelta(days=5),
        )

        url = reverse("api:budget-trends")
        response = self.client.get(url, {"months": 3})

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Check required fields
        assert "trend_data" in data
        assert "trend_indicators" in data
        assert "period_months" in data

        # Check trend data structure
        trend_data = data["trend_data"]
        assert len(trend_data) == 3  # 3 months requested

        # Each period should have required fields
        for period in trend_data:
            assert "total_budget" in period
            assert "total_spent" in period
            assert "overall_utilization_percentage" in period
            assert "period_start" in period
            assert "period_end" in period
            assert "period_label" in period

        # Check trend indicators
        indicators = data["trend_indicators"]
        assert "budget_growth" in indicators
        assert "spending_growth" in indicators
        assert "utilization_change" in indicators

    def test_budget_trends_with_category_filter(self):
        """Test budget trends endpoint with category filtering."""
        # Create budgets for different categories
        food_budget = BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="Food Budget",
            amount=Decimal("400.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        transport_budget = BudgetFactory(
            user=self.user,
            category=self.transport_category,
            name="Transport Budget",
            amount=Decimal("200.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        url = reverse("api:budget-trends")
        response = self.client.get(
            url,
            {
                "months": 2,
                "category_id": self.food_category.id,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Should include category filter in response
        assert data["category_id"] == str(self.food_category.id)

    def test_budget_trends_max_months_validation(self):
        """Test that trends endpoint validates maximum months."""
        url = reverse("api:budget-trends")
        response = self.client.get(url, {"months": 30})  # Too many months

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Maximum 24 months allowed" in response.data["error"]

    def test_budget_performance_empty_budgets(self):
        """Test performance endpoint with no budgets."""
        url = reverse("api:budget-performance")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["total_budgets"] == 0
        assert data["performance_summary"]["excellent"] == 0
        assert data["performance_details"] == []
        assert data["average_utilization"] == "0.00"

    def test_budget_analytics_user_isolation(self):
        """Test that analytics endpoints respect user isolation."""
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpass123",
        )
        other_category = CategoryFactory(user=other_user, name="Other Food")

        # Create budget for other user
        BudgetFactory(
            user=other_user,
            category=other_category,
            name="Other User Budget",
            amount=Decimal("1000.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Create budget for current user
        BudgetFactory(
            user=self.user,
            category=self.food_category,
            name="My Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        # Test analytics endpoint
        url = reverse("api:budget-analytics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Should only see current user's budget
        current = data["current_period"]
        assert Decimal(current["total_budget"]) == Decimal("500.00")
        assert current["budget_count"] == 1
