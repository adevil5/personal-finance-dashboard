"""
Tests for dashboard metrics API endpoint.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

from apps.expenses.models import Transaction
from tests.factories import CategoryFactory, TransactionFactory, UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestDashboardMetricsAPI:
    """Test dashboard metrics API endpoint."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Clear cache before each test
        cache.clear()

        # Create test categories
        self.groceries = CategoryFactory(user=self.user, name="Groceries")
        self.dining = CategoryFactory(user=self.user, name="Dining")
        self.transport = CategoryFactory(user=self.user, name="Transport")
        self.salary = CategoryFactory(user=self.user, name="Salary")

        # Create test transactions for current month
        current_date = date.today()
        self.current_month_start = date(current_date.year, current_date.month, 1)

        # Income transactions
        TransactionFactory(
            user=self.user,
            category=self.salary,
            amount=Decimal("5000.00"),
            date=self.current_month_start,
            transaction_type=Transaction.INCOME,
        )

        # Expense transactions - ensure dates don't go into future
        TransactionFactory(
            user=self.user,
            category=self.groceries,
            amount=Decimal("500.00"),
            date=min(self.current_month_start + timedelta(days=5), current_date),
            transaction_type=Transaction.EXPENSE,
        )
        TransactionFactory(
            user=self.user,
            category=self.dining,
            amount=Decimal("300.00"),
            date=min(self.current_month_start + timedelta(days=10), current_date),
            transaction_type=Transaction.EXPENSE,
        )
        TransactionFactory(
            user=self.user,
            category=self.transport,
            amount=Decimal("200.00"),
            date=min(self.current_month_start + timedelta(days=15), current_date),
            transaction_type=Transaction.EXPENSE,
        )

        # Create transactions for previous month
        if current_date.month == 1:
            prev_month = 12
            prev_year = current_date.year - 1
        else:
            prev_month = current_date.month - 1
            prev_year = current_date.year

        self.prev_month_start = date(prev_year, prev_month, 1)

        # Previous month income
        TransactionFactory(
            user=self.user,
            category=self.salary,
            amount=Decimal("5000.00"),
            date=self.prev_month_start,
            transaction_type=Transaction.INCOME,
        )

        # Previous month expenses
        TransactionFactory(
            user=self.user,
            category=self.groceries,
            amount=Decimal("600.00"),
            date=self.prev_month_start + timedelta(days=5),
            transaction_type=Transaction.EXPENSE,
        )
        TransactionFactory(
            user=self.user,
            category=self.dining,
            amount=Decimal("250.00"),
            date=self.prev_month_start + timedelta(days=10),
            transaction_type=Transaction.EXPENSE,
        )

    def test_dashboard_metrics_requires_authentication(self):
        """Test that dashboard metrics API requires authentication."""
        client = APIClient()  # Not authenticated
        url = reverse("analytics:api_dashboard_metrics")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dashboard_metrics_returns_current_month_data(self):
        """Test dashboard metrics returns current month data."""
        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "current_month" in data
        assert "metrics" in data
        assert "period" in data

        # Check current month metrics
        current_month = data["current_month"]
        assert current_month["total_income"] == 5000.0
        assert current_month["total_expenses"] == 1000.0  # 500 + 300 + 200
        assert current_month["net_savings"] == 4000.0  # 5000 - 1000
        assert current_month["savings_rate"] == 80.0  # (4000/5000) * 100

    def test_dashboard_metrics_with_month_over_month_comparison(self):
        """Test dashboard metrics with month-over-month comparison."""
        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "month_over_month" in data

        mom = data["month_over_month"]
        assert "income_change" in mom
        assert "expense_change" in mom
        assert "savings_change" in mom

        # Check month-over-month calculations
        # Income: 5000 vs 5000 = 0% change
        assert mom["income_change"]["amount"] == 0.0
        assert mom["income_change"]["percentage"] == 0.0

        # Expenses: 1000 vs 850 = +150 (+17.65%)
        assert mom["expense_change"]["amount"] == 150.0
        assert mom["expense_change"]["percentage"] == 17.65

        # Savings: 4000 vs 4150 = -150 (-3.61%)
        assert mom["savings_change"]["amount"] == -150.0
        assert mom["savings_change"]["percentage"] == -3.61

    def test_dashboard_metrics_with_no_income(self):
        """Test dashboard metrics when user has no income."""
        # Create a user with only expenses
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        category = CategoryFactory(user=user, name="Food")
        TransactionFactory(
            user=user,
            category=category,
            amount=Decimal("100.00"),
            date=date.today(),
            transaction_type=Transaction.EXPENSE,
        )

        url = reverse("analytics:api_dashboard_metrics")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        current = data["current_month"]
        assert current["total_income"] == 0.0
        assert current["total_expenses"] == 100.0
        assert current["net_savings"] == -100.0
        assert current["savings_rate"] == 0.0  # No income means 0% savings rate

    def test_dashboard_metrics_with_no_transactions(self):
        """Test dashboard metrics when user has no transactions."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        url = reverse("analytics:api_dashboard_metrics")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        current = data["current_month"]
        assert current["total_income"] == 0.0
        assert current["total_expenses"] == 0.0
        assert current["net_savings"] == 0.0
        assert current["savings_rate"] == 0.0

    def test_dashboard_metrics_includes_top_spending_categories(self):
        """Test dashboard metrics includes top spending categories."""
        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "top_categories" in data

        top_categories = data["top_categories"]
        assert len(top_categories) == 3  # We have 3 expense categories

        # Should be sorted by amount descending
        assert top_categories[0]["name"] == "Groceries"
        assert top_categories[0]["amount"] == 500.0
        assert top_categories[0]["percentage"] == 50.0  # 500/1000 * 100

        assert top_categories[1]["name"] == "Dining"
        assert top_categories[1]["amount"] == 300.0
        assert top_categories[1]["percentage"] == 30.0  # 300/1000 * 100

    def test_dashboard_metrics_includes_recent_transactions(self):
        """Test dashboard metrics includes recent transactions."""
        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "recent_transactions" in data

        recent = data["recent_transactions"]
        assert len(recent) == 5  # Default limit

        # Should be sorted by date descending
        for transaction in recent:
            assert "id" in transaction
            assert "amount" in transaction
            assert "category" in transaction
            assert "date" in transaction
            assert "transaction_type" in transaction

    def test_dashboard_metrics_with_custom_date_range(self):
        """Test dashboard metrics with custom date range."""
        # Test with specific month
        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(
            url,
            {
                "year": self.prev_month_start.year,
                "month": self.prev_month_start.month,
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        current = data["current_month"]

        # Should show previous month data
        assert current["total_income"] == 5000.0
        assert current["total_expenses"] == 850.0  # 600 + 250
        assert current["net_savings"] == 4150.0

    def test_dashboard_metrics_daily_spending_average(self):
        """Test dashboard metrics includes daily spending average."""
        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        metrics = data["metrics"]

        assert "average_daily_spending" in metrics
        # Should calculate based on days passed in current month
        days_passed = (date.today() - self.current_month_start).days + 1
        expected_avg = 1000.0 / days_passed
        assert abs(metrics["average_daily_spending"] - expected_avg) < 0.01

    def test_dashboard_metrics_transaction_count(self):
        """Test dashboard metrics includes transaction counts."""
        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        metrics = data["metrics"]

        assert "transaction_count" in metrics
        assert metrics["transaction_count"] == 4  # 1 income + 3 expenses

    def test_dashboard_metrics_caching(self):
        """Test dashboard metrics caching structure (mock in test environment)."""
        from unittest.mock import patch

        url = reverse("analytics:api_dashboard_metrics")

        # Mock cache to simulate production behavior
        mock_cache_data = {}

        def mock_cache_get(key):
            return mock_cache_data.get(key)

        def mock_cache_set(key, value, timeout):
            mock_cache_data[key] = value

        def mock_cache_delete(key):
            mock_cache_data.pop(key, None)

        with patch("apps.analytics.views.cache.get", side_effect=mock_cache_get), patch(
            "apps.analytics.views.cache.set", side_effect=mock_cache_set
        ), patch("apps.analytics.views.cache.delete", side_effect=mock_cache_delete):
            # First request should hit the database and cache result
            response1 = self.client.get(url)
            assert response1.status_code == status.HTTP_200_OK
            data1 = response1.json()

            # Verify that our mock cache has data
            current_date = date.today()
            cache_key = (
                f"dashboard_metrics_{self.user.id}_"
                f"{current_date.year}_{current_date.month}"
            )
            assert cache_key in mock_cache_data

            # Add a new transaction
            TransactionFactory(
                user=self.user,
                category=self.groceries,
                amount=Decimal("50.00"),
                date=date.today(),
                transaction_type=Transaction.EXPENSE,
            )

            # Second request should return cached data
            response2 = self.client.get(url)
            assert response2.status_code == status.HTTP_200_OK
            data2 = response2.json()

            # Should be same as cached data (not including new transaction)
            assert data1["current_month"]["total_expenses"] == (
                data2["current_month"]["total_expenses"]
            )

            # Clear cache manually
            mock_cache_data.clear()

            # Third request should hit database again
            response3 = self.client.get(url)
            assert response3.status_code == status.HTTP_200_OK
            data3 = response3.json()

            # Now should include the new transaction
            assert data3["current_month"]["total_expenses"] == 1050.0  # 1000 + 50

    def test_dashboard_metrics_user_isolation(self):
        """Test dashboard metrics only include user's own data."""
        # Create another user with transactions
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user, name="Other")

        TransactionFactory(
            user=other_user,
            category=other_category,
            amount=Decimal("10000.00"),
            date=date.today(),
            transaction_type=Transaction.EXPENSE,
        )

        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Should only show our user's transactions
        assert data["current_month"]["total_expenses"] == 1000.0

    def test_dashboard_metrics_budget_status(self):
        """Test dashboard metrics includes budget status summary."""
        from apps.budgets.models import Budget

        # Create budgets for current month
        Budget.objects.create(
            user=self.user,
            name="Groceries Budget",
            category=self.groceries,
            amount=Decimal("400.00"),  # Over budget (spent 500)
            period_start=self.current_month_start,
            period_end=self.current_month_start + timedelta(days=30),
        )
        Budget.objects.create(
            user=self.user,
            name="Dining Budget",
            category=self.dining,
            amount=Decimal("500.00"),  # Under budget (spent 300)
            period_start=self.current_month_start,
            period_end=self.current_month_start + timedelta(days=30),
        )

        url = reverse("analytics:api_dashboard_metrics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "budget_summary" in data

        budget_summary = data["budget_summary"]
        assert budget_summary["total_budgets"] == 2
        assert budget_summary["over_budget_count"] == 1
        assert budget_summary["total_budget_amount"] == 900.0
        assert budget_summary["total_budget_spent"] == 800.0  # 500 + 300
        # (800/900) * 100
        assert budget_summary["overall_utilization"] == 88.89

    def test_dashboard_metrics_error_handling(self):
        """Test dashboard metrics error handling for invalid parameters."""
        url = reverse("analytics:api_dashboard_metrics")

        # Invalid year
        response = self.client.get(url, {"year": "invalid"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

        # Invalid month
        response = self.client.get(url, {"month": "13"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

        # Future date
        response = self.client.get(
            url,
            {
                "year": date.today().year + 1,
                "month": 1,
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()


@pytest.mark.django_db
class TestDashboardMetricsPerformance:
    """Test dashboard metrics performance with large datasets."""

    def test_dashboard_metrics_with_many_transactions(self):
        """Test dashboard metrics performance with many transactions."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        category = CategoryFactory(user=user, name="Test")

        # Create 500 transactions
        transactions = []
        for i in range(500):
            transaction_date = date.today() - timedelta(days=i % 30)
            trans_type = Transaction.EXPENSE if i % 2 == 0 else Transaction.INCOME
            transactions.append(
                Transaction(
                    user=user,
                    category=category,
                    amount=Decimal("50.00"),
                    date=transaction_date,
                    transaction_type=trans_type,
                )
            )
        Transaction.objects.bulk_create(transactions)

        import time

        start_time = time.time()

        url = reverse("analytics:api_dashboard_metrics")
        response = client.get(url)

        end_time = time.time()

        assert response.status_code == status.HTTP_200_OK
        # Should complete within 2 seconds even with many transactions
        assert (end_time - start_time) < 2.0

        # Verify data is correct
        data = response.json()
        assert data["metrics"]["transaction_count"] > 0
