"""
Tests for comprehensive analytics API endpoints.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.expenses.models import Transaction
from tests.factories import CategoryFactory, TransactionFactory, UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestSpendingTrendsAPI:
    """Test spending trends API endpoint."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create test categories
        self.groceries = CategoryFactory(user=self.user, name="Groceries")
        self.dining = CategoryFactory(user=self.user, name="Dining")

        # Create test transactions across multiple days
        base_date = date.today() - timedelta(days=10)

        # Day 1: $100 groceries
        TransactionFactory(
            user=self.user,
            category=self.groceries,
            amount=Decimal("100.00"),
            date=base_date,
            transaction_type=Transaction.EXPENSE,
        )

        # Day 3: $50 dining
        TransactionFactory(
            user=self.user,
            category=self.dining,
            amount=Decimal("50.00"),
            date=base_date + timedelta(days=2),
            transaction_type=Transaction.EXPENSE,
        )

        # Day 5: $75 groceries
        TransactionFactory(
            user=self.user,
            category=self.groceries,
            amount=Decimal("75.00"),
            date=base_date + timedelta(days=4),
            transaction_type=Transaction.EXPENSE,
        )

    def test_spending_trends_requires_authentication(self):
        """Test that spending trends API requires authentication."""
        client = APIClient()  # Not authenticated
        url = reverse("analytics:api_spending_trends")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_spending_trends_daily(self):
        """Test daily spending trends endpoint."""
        url = reverse("analytics:api_spending_trends")
        response = self.client.get(url, {"period": "daily"})

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "trends" in data
        assert "period" in data
        assert data["period"] == "daily"

        trends = data["trends"]
        assert isinstance(trends, list)
        assert len(trends) > 0

        # Check data structure
        for trend in trends:
            assert "date" in trend
            assert "amount" in trend

    def test_spending_trends_weekly(self):
        """Test weekly spending trends endpoint."""
        url = reverse("analytics:api_spending_trends")
        response = self.client.get(url, {"period": "weekly"})

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["period"] == "weekly"
        assert "trends" in data

    def test_spending_trends_monthly(self):
        """Test monthly spending trends endpoint."""
        url = reverse("analytics:api_spending_trends")
        response = self.client.get(url, {"period": "monthly"})

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["period"] == "monthly"
        assert "trends" in data

    def test_spending_trends_invalid_period(self):
        """Test spending trends with invalid period."""
        url = reverse("analytics:api_spending_trends")
        response = self.client.get(url, {"period": "invalid"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_spending_trends_with_date_range(self):
        """Test spending trends with custom date range."""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        url = reverse("analytics:api_spending_trends")
        response = self.client.get(
            url,
            {
                "period": "daily",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["date_range"]["start_date"] == start_date.isoformat()
        assert data["date_range"]["end_date"] == end_date.isoformat()

    def test_spending_trends_user_isolation(self):
        """Test that spending trends only include user's data."""
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user, name="Other")

        # Create transaction for other user
        TransactionFactory(
            user=other_user,
            category=other_category,
            amount=Decimal("1000.00"),
            date=date.today() - timedelta(days=5),
            transaction_type=Transaction.EXPENSE,
        )

        url = reverse("analytics:api_spending_trends")
        response = self.client.get(url, {"period": "daily"})

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        trends = data["trends"]

        # Should only include our user's transactions ($225 total)
        total_from_trends = sum(Decimal(str(trend["amount"])) for trend in trends)
        assert total_from_trends == Decimal("225.00")


@pytest.mark.django_db
class TestCategoryBreakdownAPI:
    """Test category breakdown API endpoint."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create test categories and transactions
        self.groceries = CategoryFactory(user=self.user, name="Groceries")
        self.dining = CategoryFactory(user=self.user, name="Dining")
        self.transport = CategoryFactory(user=self.user, name="Transport")

        TransactionFactory(
            user=self.user,
            category=self.groceries,
            amount=Decimal("200.00"),
            date=date.today() - timedelta(days=5),
            transaction_type=Transaction.EXPENSE,
        )
        TransactionFactory(
            user=self.user,
            category=self.dining,
            amount=Decimal("150.00"),
            date=date.today() - timedelta(days=3),
            transaction_type=Transaction.EXPENSE,
        )
        TransactionFactory(
            user=self.user,
            category=self.transport,
            amount=Decimal("50.00"),
            date=date.today() - timedelta(days=1),
            transaction_type=Transaction.EXPENSE,
        )

    def test_category_breakdown_requires_authentication(self):
        """Test that category breakdown API requires authentication."""
        client = APIClient()  # Not authenticated
        url = reverse("analytics:api_category_breakdown")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_category_breakdown_returns_data(self):
        """Test category breakdown endpoint returns proper data."""
        url = reverse("analytics:api_category_breakdown")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "categories" in data
        assert "total_spending" in data
        assert "category_count" in data

        categories = data["categories"]
        assert len(categories) == 3

        # Check data structure and values
        category_names = [cat["name"] for cat in categories]
        assert "Groceries" in category_names
        assert "Dining" in category_names
        assert "Transport" in category_names

        # Check amounts (should be sorted by amount descending)
        assert categories[0]["amount"] == 200.0  # Groceries
        assert categories[1]["amount"] == 150.0  # Dining
        assert categories[2]["amount"] == 50.0  # Transport

        # Check percentages
        assert categories[0]["percentage"] == 50.0  # 200/400 * 100
        assert categories[1]["percentage"] == 37.5  # 150/400 * 100
        assert categories[2]["percentage"] == 12.5  # 50/400 * 100

        assert data["total_spending"] == 400.0

    def test_category_breakdown_with_date_range(self):
        """Test category breakdown with custom date range."""
        start_date = date.today() - timedelta(days=4)
        end_date = date.today()

        url = reverse("analytics:api_category_breakdown")
        response = self.client.get(
            url,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Should exclude the groceries transaction from 5 days ago
        assert data["total_spending"] == 200.0  # Only dining + transport
        assert len(data["categories"]) == 2

    def test_category_breakdown_user_isolation(self):
        """Test that category breakdown only includes user's data."""
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user, name="Other")

        TransactionFactory(
            user=other_user,
            category=other_category,
            amount=Decimal("1000.00"),
            date=date.today() - timedelta(days=2),
            transaction_type=Transaction.EXPENSE,
        )

        url = reverse("analytics:api_category_breakdown")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Should only include our user's categories
        assert data["total_spending"] == 400.0
        assert len(data["categories"]) == 3


@pytest.mark.django_db
class TestSpendingComparisonAPI:
    """Test spending comparison API endpoint."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.category = CategoryFactory(user=self.user, name="Groceries")

        # Current period transactions (last 7 days)
        for i in range(7):
            TransactionFactory(
                user=self.user,
                category=self.category,
                amount=Decimal("20.00"),
                date=date.today() - timedelta(days=i),
                transaction_type=Transaction.EXPENSE,
            )

        # Previous period transactions (8-14 days ago)
        for i in range(7, 14):
            TransactionFactory(
                user=self.user,
                category=self.category,
                amount=Decimal("10.00"),
                date=date.today() - timedelta(days=i),
                transaction_type=Transaction.EXPENSE,
            )

    def test_spending_comparison_requires_authentication(self):
        """Test that spending comparison API requires authentication."""
        client = APIClient()  # Not authenticated
        url = reverse("analytics:api_spending_comparison")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_spending_comparison_returns_data(self):
        """Test spending comparison endpoint returns proper data."""
        current_start = date.today() - timedelta(days=6)
        current_end = date.today()
        comparison_start = date.today() - timedelta(days=13)
        comparison_end = date.today() - timedelta(days=7)

        url = reverse("analytics:api_spending_comparison")
        response = self.client.get(
            url,
            {
                "current_start": current_start.isoformat(),
                "current_end": current_end.isoformat(),
                "comparison_start": comparison_start.isoformat(),
                "comparison_end": comparison_end.isoformat(),
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "current_period" in data
        assert "comparison_period" in data
        assert "change_amount" in data
        assert "change_percentage" in data

        # Check values - current: 7*20 = 140, comparison: 7*10 = 70
        assert data["current_period"] == 140.0
        assert data["comparison_period"] == 70.0
        assert data["change_amount"] == 70.0  # 140 - 70
        assert data["change_percentage"] == 100.0  # 70/70 * 100

    def test_spending_comparison_missing_parameters(self):
        """Test spending comparison with missing parameters."""
        url = reverse("analytics:api_spending_comparison")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()


@pytest.mark.django_db
class TestTopCategoriesAPI:
    """Test top categories API endpoint."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create multiple categories with different spending amounts
        categories_data = [
            ("Groceries", "300.00"),
            ("Dining", "200.00"),
            ("Transport", "150.00"),
            ("Entertainment", "100.00"),
            ("Shopping", "75.00"),
            ("Utilities", "50.00"),
        ]

        for cat_name, amount in categories_data:
            category = CategoryFactory(user=self.user, name=cat_name)
            TransactionFactory(
                user=self.user,
                category=category,
                amount=Decimal(amount),
                date=date.today() - timedelta(days=5),
                transaction_type=Transaction.EXPENSE,
            )

    def test_top_categories_requires_authentication(self):
        """Test that top categories API requires authentication."""
        client = APIClient()  # Not authenticated
        url = reverse("analytics:api_top_categories")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_top_categories_returns_data(self):
        """Test top categories endpoint returns proper data."""
        url = reverse("analytics:api_top_categories")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "categories" in data
        assert "limit" in data

        categories = data["categories"]
        assert len(categories) == 5  # Default limit

        # Check sorting (highest to lowest)
        assert categories[0]["category"] == "Groceries"
        assert categories[0]["amount"] == 300.0
        assert categories[1]["category"] == "Dining"
        assert categories[1]["amount"] == 200.0

    def test_top_categories_with_custom_limit(self):
        """Test top categories with custom limit."""
        url = reverse("analytics:api_top_categories")
        response = self.client.get(url, {"limit": "3"})

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["categories"]) == 3
        assert data["limit"] == 3


@pytest.mark.django_db
class TestDayOfWeekAnalysisAPI:
    """Test day of week spending analysis API endpoint."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.category = CategoryFactory(user=self.user, name="Groceries")

        # Create transactions on different days of week
        # Monday
        TransactionFactory(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            date=date(2024, 1, 1),  # Known Monday
            transaction_type=Transaction.EXPENSE,
        )
        # Friday
        TransactionFactory(
            user=self.user,
            category=self.category,
            amount=Decimal("150.00"),
            date=date(2024, 1, 5),  # Known Friday
            transaction_type=Transaction.EXPENSE,
        )

    def test_day_of_week_requires_authentication(self):
        """Test that day of week analysis API requires authentication."""
        client = APIClient()  # Not authenticated
        url = reverse("analytics:api_day_of_week")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_day_of_week_returns_data(self):
        """Test day of week analysis endpoint returns proper data."""
        url = reverse("analytics:api_day_of_week")
        response = self.client.get(
            url,
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "spending_by_day" in data
        assert "total_spending" in data

        spending_by_day = data["spending_by_day"]

        # Check all days are present
        expected_days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        for day in expected_days:
            assert day in spending_by_day

        # Check specific values
        assert spending_by_day["Monday"] == 100.0
        assert spending_by_day["Friday"] == 150.0
        assert spending_by_day["Tuesday"] == 0.0  # No transactions


@pytest.mark.django_db
class TestAnalyticsAPIPerformance:
    """Test analytics API performance with large datasets."""

    def test_analytics_with_large_dataset(self):
        """Test analytics endpoints with large number of transactions."""
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        category = CategoryFactory(user=user, name="Test Category")

        # Create 1000 transactions
        transactions = []
        for i in range(1000):
            transactions.append(
                TransactionFactory(
                    user=user,
                    category=category,
                    amount=Decimal("10.00"),
                    date=date.today() - timedelta(days=i % 365),
                    transaction_type=Transaction.EXPENSE,
                )
            )

        # Test trends endpoint
        url = reverse("analytics:api_spending_trends")
        response = client.get(url, {"period": "monthly"})
        assert response.status_code == status.HTTP_200_OK

        # Test category breakdown endpoint with date range to include all transactions
        start_date = (date.today() - timedelta(days=365)).isoformat()
        end_date = date.today().isoformat()

        url = reverse("analytics:api_category_breakdown")
        response = client.get(
            url,
            {
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify the data is correct
        data = response.json()
        assert data["total_spending"] == 10000.0  # 1000 * 10.00

    def test_analytics_api_response_time(self):
        """Test that analytics API responses are reasonably fast."""
        import time

        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        category = CategoryFactory(user=user, name="Test Category")

        # Create 500 transactions
        for i in range(500):
            TransactionFactory(
                user=user,
                category=category,
                amount=Decimal("25.00"),
                date=date.today() - timedelta(days=i % 180),
                transaction_type=Transaction.EXPENSE,
            )

        # Test response times
        endpoints = [
            reverse("analytics:api_spending_trends"),
            reverse("analytics:api_category_breakdown"),
            reverse("analytics:api_top_categories"),
            reverse("analytics:api_day_of_week"),
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()

            assert response.status_code == status.HTTP_200_OK
            # Response should be under 2 seconds
            assert (end_time - start_time) < 2.0


@pytest.mark.django_db
class TestAnalyticsAPIErrorHandling:
    """Test analytics API error handling scenarios."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_invalid_date_format(self):
        """Test API response to invalid date formats."""
        url = reverse("analytics:api_spending_trends")
        response = self.client.get(
            url,
            {
                "start_date": "invalid-date",
                "end_date": "2024-01-01",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_start_date_after_end_date(self):
        """Test API response when start date is after end date."""
        url = reverse("analytics:api_category_breakdown")
        response = self.client.get(
            url,
            {
                "start_date": "2024-01-10",
                "end_date": "2024-01-01",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_no_data_scenarios(self):
        """Test API responses when no data is available."""
        # No transactions exist for this user
        endpoints = [
            reverse("analytics:api_spending_trends"),
            reverse("analytics:api_category_breakdown"),
            reverse("analytics:api_top_categories"),
            reverse("analytics:api_day_of_week"),
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == status.HTTP_200_OK

            # Should return empty or zero data, not error
            data = response.json()
            assert isinstance(data, dict)
