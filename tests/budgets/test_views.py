from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.budgets.models import Budget
from apps.expenses.models import Transaction
from tests.factories import BudgetFactory, CategoryFactory, TransactionFactory

User = get_user_model()


@pytest.mark.django_db
class TestBudgetViewSet:
    """Test BudgetViewSet CRUD operations."""

    def setup_method(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpass123",
        )
        self.client.force_authenticate(user=self.user)

        # Create categories for testing
        self.category1 = CategoryFactory(user=self.user, name="Food")
        self.category2 = CategoryFactory(user=self.user, name="Transport")
        self.other_category = CategoryFactory(user=self.other_user, name="Other")

        # Create test budgets
        self.current_month_start = date.today().replace(day=1)
        self.current_month_end = (
            self.current_month_start + timedelta(days=32)
        ).replace(day=1) - timedelta(days=1)

        self.budget1 = BudgetFactory(
            user=self.user,
            category=self.category1,
            name="Food Budget",
            amount=Decimal("500.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        self.budget2 = BudgetFactory(
            user=self.user,
            category=self.category2,
            name="Transport Budget",
            amount=Decimal("200.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

        self.other_budget = BudgetFactory(
            user=self.other_user,
            category=None,  # Overall budget without category
            name="Other User Budget",
            amount=Decimal("1000.00"),
            period_start=self.current_month_start,
            period_end=self.current_month_end,
        )

    def test_list_budgets(self):
        """Test listing budgets for authenticated user."""
        url = reverse("api:budget-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

        # Verify only user's budgets are returned
        budget_ids = [b["id"] for b in response.data["results"]]
        assert self.budget1.id in budget_ids
        assert self.budget2.id in budget_ids
        assert self.other_budget.id not in budget_ids

    def test_retrieve_budget(self):
        """Test retrieving a single budget."""
        url = reverse("api:budget-detail", kwargs={"pk": self.budget1.pk})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.budget1.id
        assert response.data["name"] == "Food Budget"
        assert Decimal(response.data["amount"]) == Decimal("500.00")
        assert response.data["category"]["id"] == self.category1.id

    def test_retrieve_other_user_budget_forbidden(self):
        """Test that users cannot retrieve other users' budgets."""
        url = reverse("api:budget-detail", kwargs={"pk": self.other_budget.pk})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_budget_with_category(self):
        """Test creating a budget with a category."""
        # Create a new category for this test to avoid conflicts
        new_category = CategoryFactory(user=self.user, name="Entertainment")

        url = reverse("api:budget-list")
        data = {
            "name": "Entertainment Budget",
            "amount": "750.00",
            "category_id": new_category.id,
            "period_start": str(self.current_month_start),
            "period_end": str(self.current_month_end),
            "alert_enabled": True,
            "warning_threshold": "80.00",
            "critical_threshold": "100.00",
        }
        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Entertainment Budget"
        assert Decimal(response.data["amount"]) == Decimal("750.00")
        assert response.data["category"]["id"] == new_category.id
        assert response.data["alert_enabled"] is True
        assert Decimal(response.data["warning_threshold"]) == Decimal("80.00")

        # Verify in database
        budget = Budget.objects.get(id=response.data["id"])
        assert budget.user == self.user
        assert budget.amount == Decimal("750.00")

    def test_create_overall_budget_without_category(self):
        """Test creating an overall budget without category."""
        url = reverse("api:budget-list")
        data = {
            "name": "Overall Monthly Budget",
            "amount": "2000.00",
            "period_start": str(self.current_month_start),
            "period_end": str(self.current_month_end),
        }
        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Overall Monthly Budget"
        assert response.data["category"] is None

    def test_create_budget_with_other_user_category_fails(self):
        """Test that creating a budget with another user's category fails."""
        url = reverse("api:budget-list")
        data = {
            "name": "Invalid Budget",
            "amount": "500.00",
            "category_id": self.other_category.id,
            "period_start": str(self.current_month_start),
            "period_end": str(self.current_month_end),
        }
        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "category_id" in response.data

    def test_update_budget(self):
        """Test updating a budget."""
        url = reverse("api:budget-detail", kwargs={"pk": self.budget1.pk})
        data = {
            "name": "Updated Food Budget",
            "amount": "600.00",
            "category_id": self.category1.id,
            "period_start": str(self.budget1.period_start),
            "period_end": str(self.budget1.period_end),
        }
        response = self.client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Food Budget"
        assert Decimal(response.data["amount"]) == Decimal("600.00")

        # Verify in database
        self.budget1.refresh_from_db()
        assert self.budget1.name == "Updated Food Budget"
        assert self.budget1.amount == Decimal("600.00")

    def test_partial_update_budget(self):
        """Test partial update of a budget."""
        url = reverse("api:budget-detail", kwargs={"pk": self.budget1.pk})
        data = {"amount": "550.00"}
        response = self.client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["amount"]) == Decimal("550.00")
        assert response.data["name"] == "Food Budget"  # Unchanged

    def test_delete_budget(self):
        """Test soft deleting a budget."""
        url = reverse("api:budget-detail", kwargs={"pk": self.budget1.pk})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify soft delete
        self.budget1.refresh_from_db()
        assert self.budget1.is_active is False

    def test_budget_includes_calculations(self):
        """Test that budget response includes calculated fields."""
        # Create some transactions for the budget
        # Use safe dates that are definitely in the past or today
        today = date.today()
        transaction_date1 = min(self.current_month_start + timedelta(days=5), today)
        transaction_date2 = min(self.current_month_start + timedelta(days=10), today)

        TransactionFactory(
            user=self.user,
            category=self.category1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=transaction_date1,
        )
        TransactionFactory(
            user=self.user,
            category=self.category1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("75.50"),
            date=transaction_date2,
        )

        url = reverse("api:budget-detail", kwargs={"pk": self.budget1.pk})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "spent_amount" in response.data
        assert "remaining_amount" in response.data
        assert "utilization_percentage" in response.data
        assert "is_over_budget" in response.data

        assert Decimal(response.data["spent_amount"]) == Decimal("225.50")
        assert Decimal(response.data["remaining_amount"]) == Decimal("274.50")
        assert Decimal(response.data["utilization_percentage"]) == Decimal("45.10")
        assert response.data["is_over_budget"] is False

    def test_period_based_filtering(self):
        """Test filtering budgets by period."""
        # Create budgets for different periods
        last_month_start = (self.current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = self.current_month_start - timedelta(days=1)

        BudgetFactory(
            user=self.user,
            category=None,  # Overall budget without category
            name="Past Budget",
            amount=Decimal("300.00"),
            period_start=last_month_start,
            period_end=last_month_end,
        )

        # Filter for current period
        url = reverse("api:budget-list")
        response = self.client.get(
            url,
            {
                "period_start_after": str(self.current_month_start),
                "period_end_before": str(self.current_month_end),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        budget_names = [b["name"] for b in response.data["results"]]
        assert "Past Budget" not in budget_names

    def test_filter_by_category(self):
        """Test filtering budgets by category."""
        url = reverse("api:budget-list")
        response = self.client.get(url, {"category": self.category1.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == self.budget1.id

    def test_filter_active_budgets(self):
        """Test filtering only active budgets."""
        # Soft delete one budget
        self.budget1.is_active = False
        self.budget1.save()

        url = reverse("api:budget-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == self.budget2.id

    def test_budget_ordering(self):
        """Test budget ordering by period and name."""
        url = reverse("api:budget-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Should be ordered by -period_start, name by default
        results = response.data["results"]
        assert results[0]["name"] == "Food Budget"
        assert results[1]["name"] == "Transport Budget"

    def test_unauthenticated_access_forbidden(self):
        """Test that unauthenticated users cannot access budgets."""
        self.client.force_authenticate(user=None)
        url = reverse("api:budget-list")
        response = self.client.get(url)

        # DRF returns 403 when authentication is required but not provided
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_duplicate_budget_fails(self):
        """Test that creating duplicate budget for same period/category fails."""
        url = reverse("api:budget-list")
        data = {
            "name": "Duplicate Food Budget",
            "amount": "400.00",
            "category_id": self.category1.id,
            "period_start": str(self.budget1.period_start),
            "period_end": str(self.budget1.period_end),
        }
        response = self.client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_budget_statistics_action(self):
        """Test budget statistics endpoint."""
        # Create transactions with safe dates
        today = date.today()
        transaction_date1 = min(self.current_month_start + timedelta(days=5), today)
        transaction_date2 = min(self.current_month_start + timedelta(days=10), today)

        TransactionFactory(
            user=self.user,
            category=self.category1,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("300.00"),
            date=transaction_date1,
        )
        TransactionFactory(
            user=self.user,
            category=self.category2,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("150.00"),
            date=transaction_date2,
        )

        url = reverse("api:budget-statistics")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "total_budget" in response.data
        assert "total_spent" in response.data
        assert "total_remaining" in response.data
        assert "overall_utilization_percentage" in response.data
        assert "budget_count" in response.data
        assert "over_budget_count" in response.data

        assert Decimal(response.data["total_budget"]) == Decimal("700.00")  # 500 + 200
        assert Decimal(response.data["total_spent"]) == Decimal("450.00")  # 300 + 150
        assert Decimal(response.data["total_remaining"]) == Decimal("250.00")

    def test_current_budgets_action(self):
        """Test endpoint to get current period budgets."""
        # Create a future budget
        future_start = self.current_month_end + timedelta(days=1)
        future_end = (future_start + timedelta(days=32)).replace(day=1) - timedelta(
            days=1
        )

        BudgetFactory(
            user=self.user,
            category=None,  # Overall budget without category
            name="Future Budget",
            amount=Decimal("1000.00"),
            period_start=future_start,
            period_end=future_end,
        )

        url = reverse("api:budget-current")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2  # Only current budgets
        budget_names = [b["name"] for b in response.data]
        assert "Future Budget" not in budget_names
