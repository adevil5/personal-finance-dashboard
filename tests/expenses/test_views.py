from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.expenses.models import Transaction
from tests.factories import CategoryFactory, TransactionFactory, UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestTransactionViewSet:
    """Test suite for Transaction API endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create API client."""
        return APIClient()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return UserFactory()

    @pytest.fixture
    def other_user(self):
        """Create another test user."""
        return UserFactory()

    @pytest.fixture
    def auth_client(self, api_client, user):
        """Create authenticated API client."""
        # Create token for user
        token, _ = Token.objects.get_or_create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return api_client

    @pytest.fixture
    def category(self, user):
        """Create test category."""
        return CategoryFactory(user=user)

    @pytest.fixture
    def transaction(self, user, category):
        """Create test transaction."""
        return TransactionFactory(
            user=user,
            category=category,
            transaction_type=Transaction.EXPENSE,
        )

    def test_list_transactions_requires_authentication(self, api_client):
        """Test that listing transactions requires authentication."""
        url = reverse("api:transaction-list")
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_transactions_returns_only_user_transactions(
        self, auth_client, user, other_user, category
    ):
        """Test that users can only see their own transactions."""
        # Create transactions for both users
        transaction1 = TransactionFactory(user=user, category=category)
        transaction2 = TransactionFactory(user=user, category=category)
        other_category = CategoryFactory(user=other_user)
        TransactionFactory(user=other_user, category=other_category)

        url = reverse("api:transaction-list")
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        transaction_ids = [t["id"] for t in response.data["results"]]
        assert transaction1.id in transaction_ids
        assert transaction2.id in transaction_ids

    def test_create_expense_transaction(self, auth_client, user, category):
        """Test creating an expense transaction."""
        url = reverse("api:transaction-list")
        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Test expense",
            "date": date.today().isoformat(),
            "merchant": "Test Store",
            "notes": "Test notes",
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["transaction_type"] == Transaction.EXPENSE
        assert Decimal(response.data["amount"]) == Decimal("50.00")
        assert response.data["category"]["id"] == category.id
        assert response.data["description"] == "Test expense"
        assert response.data["merchant"] == "Test Store"
        assert response.data["notes"] == "Test notes"

        # Verify transaction was created
        transaction = Transaction.objects.get(id=response.data["id"])
        assert transaction.user == user
        assert transaction.amount == Decimal("50.00")

    def test_create_income_transaction(self, auth_client, user):
        """Test creating an income transaction without category."""
        url = reverse("api:transaction-list")
        data = {
            "transaction_type": Transaction.INCOME,
            "amount": "1000.00",
            "description": "Salary",
            "date": date.today().isoformat(),
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["transaction_type"] == Transaction.INCOME
        assert Decimal(response.data["amount"]) == Decimal("1000.00")
        assert response.data["category"] is None

    def test_create_expense_without_category_fails(self, auth_client, user):
        """Test that creating expense without category fails."""
        url = reverse("api:transaction-list")
        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "description": "Test expense",
            "date": date.today().isoformat(),
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "category" in response.data

    def test_create_transaction_with_invalid_amount_fails(self, auth_client, category):
        """Test that creating transaction with invalid amount fails."""
        url = reverse("api:transaction-list")
        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "-50.00",
            "category_id": category.id,
            "description": "Test expense",
            "date": date.today().isoformat(),
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "amount" in response.data

    def test_create_transaction_with_future_date_fails(self, auth_client, category):
        """Test that creating transaction with future date fails."""
        url = reverse("api:transaction-list")
        future_date = date.today() + timedelta(days=1)
        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Test expense",
            "date": future_date.isoformat(),
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "date" in response.data

    def test_retrieve_transaction(self, auth_client, transaction):
        """Test retrieving a single transaction."""
        url = reverse("api:transaction-detail", kwargs={"pk": transaction.id})
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == transaction.id
        assert Decimal(response.data["amount"]) == transaction.amount
        assert response.data["description"] == transaction.description

    def test_retrieve_other_user_transaction_fails(
        self, auth_client, other_user, category
    ):
        """Test that users cannot retrieve other users' transactions."""
        other_category = CategoryFactory(user=other_user)
        other_transaction = TransactionFactory(user=other_user, category=other_category)

        url = reverse("api:transaction-detail", kwargs={"pk": other_transaction.id})
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_transaction(self, auth_client, transaction):
        """Test updating a transaction."""
        url = reverse("api:transaction-detail", kwargs={"pk": transaction.id})
        data = {
            "transaction_type": transaction.transaction_type,
            "amount": "75.50",
            "category_id": transaction.category.id,
            "description": "Updated description",
            "date": transaction.date.isoformat(),
        }

        response = auth_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["amount"]) == Decimal("75.50")
        assert response.data["description"] == "Updated description"

        # Verify update in database
        transaction.refresh_from_db()
        assert transaction.amount == Decimal("75.50")
        assert transaction.description == "Updated description"

    def test_partial_update_transaction(self, auth_client, transaction):
        """Test partial update of a transaction."""
        url = reverse("api:transaction-detail", kwargs={"pk": transaction.id})
        data = {"description": "Partially updated"}

        response = auth_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["description"] == "Partially updated"

    def test_delete_transaction(self, auth_client, transaction):
        """Test deleting a transaction."""
        url = reverse("api:transaction-detail", kwargs={"pk": transaction.id})
        response = auth_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Verify soft delete - transaction still exists but is_active=False
        transaction.refresh_from_db()
        assert not transaction.is_active

    def test_delete_other_user_transaction_fails(
        self, auth_client, other_user, category
    ):
        """Test that users cannot delete other users' transactions."""
        other_category = CategoryFactory(user=other_user)
        other_transaction = TransactionFactory(user=other_user, category=other_category)

        url = reverse("api:transaction-detail", kwargs={"pk": other_transaction.id})
        response = auth_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Verify transaction was not affected
        other_transaction.refresh_from_db()
        assert other_transaction.is_active

    def test_filter_transactions_by_date_range(self, auth_client, user, category):
        """Test filtering transactions by date range."""
        # Create transactions with different dates
        today = date.today()
        TransactionFactory(user=user, category=category, date=today - timedelta(days=5))
        transaction2 = TransactionFactory(
            user=user, category=category, date=today - timedelta(days=2)
        )
        transaction3 = TransactionFactory(user=user, category=category, date=today)
        TransactionFactory(
            user=user, category=category, date=today - timedelta(days=10)
        )

        # Filter for last 3 days
        url = reverse("api:transaction-list")
        response = auth_client.get(
            url,
            {
                "date_after": (today - timedelta(days=3)).isoformat(),
                "date_before": today.isoformat(),
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        transaction_ids = [t["id"] for t in response.data["results"]]
        assert transaction2.id in transaction_ids
        assert transaction3.id in transaction_ids

    def test_filter_transactions_by_category(self, auth_client, user):
        """Test filtering transactions by category."""
        category1 = CategoryFactory(user=user, name="Food")
        category2 = CategoryFactory(user=user, name="Transport")

        transaction1 = TransactionFactory(user=user, category=category1)
        TransactionFactory(user=user, category=category2)
        transaction3 = TransactionFactory(user=user, category=category1)

        url = reverse("api:transaction-list")
        response = auth_client.get(url, {"category": category1.id})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        transaction_ids = [t["id"] for t in response.data["results"]]
        assert transaction1.id in transaction_ids
        assert transaction3.id in transaction_ids

    def test_filter_transactions_by_amount_range(self, auth_client, user, category):
        """Test filtering transactions by amount range."""
        TransactionFactory(user=user, category=category, amount=Decimal("25.00"))
        transaction2 = TransactionFactory(
            user=user, category=category, amount=Decimal("50.00")
        )
        transaction3 = TransactionFactory(
            user=user, category=category, amount=Decimal("75.00")
        )
        TransactionFactory(user=user, category=category, amount=Decimal("100.00"))

        url = reverse("api:transaction-list")
        response = auth_client.get(
            url,
            {
                "amount_min": "40.00",
                "amount_max": "80.00",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        transaction_ids = [t["id"] for t in response.data["results"]]
        assert transaction2.id in transaction_ids
        assert transaction3.id in transaction_ids

    def test_filter_transactions_by_type(self, auth_client, user, category):
        """Test filtering transactions by transaction type."""
        expense = TransactionFactory(
            user=user, category=category, transaction_type=Transaction.EXPENSE
        )
        TransactionFactory(
            user=user, category=None, transaction_type=Transaction.INCOME
        )
        expense2 = TransactionFactory(
            user=user, category=category, transaction_type=Transaction.EXPENSE
        )

        url = reverse("api:transaction-list")
        response = auth_client.get(url, {"transaction_type": Transaction.EXPENSE})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        transaction_ids = [t["id"] for t in response.data["results"]]
        assert expense.id in transaction_ids
        assert expense2.id in transaction_ids

    def test_search_transactions(self, auth_client, user, category):
        """Test searching transactions by description and merchant."""
        transaction1 = TransactionFactory(
            user=user,
            category=category,
            description="Coffee at Starbucks",
            merchant="Starbucks",
        )
        transaction2 = TransactionFactory(
            user=user,
            category=category,
            description="Lunch at restaurant",
            merchant="Local Diner",
        )
        TransactionFactory(
            user=user,
            category=category,
            description="Gas",
            merchant="Shell",
        )

        # Search for "coffee" or "starbucks"
        url = reverse("api:transaction-list")
        response = auth_client.get(url, {"search": "starbucks"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == transaction1.id

        # Search for "lunch"
        response = auth_client.get(url, {"search": "lunch"})
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == transaction2.id

    def test_order_transactions_by_date(self, auth_client, user, category):
        """Test ordering transactions by date."""
        today = date.today()
        transaction1 = TransactionFactory(
            user=user, category=category, date=today - timedelta(days=2)
        )
        transaction2 = TransactionFactory(user=user, category=category, date=today)
        transaction3 = TransactionFactory(
            user=user, category=category, date=today - timedelta(days=1)
        )

        # Order by date ascending
        url = reverse("api:transaction-list")
        response = auth_client.get(url, {"ordering": "date"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert results[0]["id"] == transaction1.id
        assert results[1]["id"] == transaction3.id
        assert results[2]["id"] == transaction2.id

        # Order by date descending (default)
        response = auth_client.get(url, {"ordering": "-date"})
        results = response.data["results"]
        assert results[0]["id"] == transaction2.id
        assert results[1]["id"] == transaction3.id
        assert results[2]["id"] == transaction1.id

    def test_order_transactions_by_amount(self, auth_client, user, category):
        """Test ordering transactions by amount."""
        transaction1 = TransactionFactory(
            user=user, category=category, amount=Decimal("50.00")
        )
        transaction2 = TransactionFactory(
            user=user, category=category, amount=Decimal("100.00")
        )
        transaction3 = TransactionFactory(
            user=user, category=category, amount=Decimal("25.00")
        )

        url = reverse("api:transaction-list")
        response = auth_client.get(url, {"ordering": "amount_index"})

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert results[0]["id"] == transaction3.id
        assert results[1]["id"] == transaction1.id
        assert results[2]["id"] == transaction2.id

    def test_pagination(self, auth_client, user, category):
        """Test pagination of transaction list."""
        # Create 25 transactions
        for i in range(25):
            TransactionFactory(
                user=user,
                category=category,
                amount=Decimal(f"{i+1}.00"),
            )

        url = reverse("api:transaction-list")
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 25
        assert len(response.data["results"]) == 20  # Default page size
        assert response.data["next"] is not None
        assert response.data["previous"] is None

        # Get second page
        response = auth_client.get(url, {"page": 2})
        assert len(response.data["results"]) == 5
        assert response.data["next"] is None
        assert response.data["previous"] is not None

    def test_recurring_transaction_creation(self, auth_client, user, category):
        """Test creating a recurring transaction."""
        url = reverse("api:transaction-list")
        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Monthly subscription",
            "date": date.today().isoformat(),
            "is_recurring": True,
            "recurring_frequency": Transaction.MONTHLY,
            "recurring_interval": 1,
            "recurring_start_date": date.today().isoformat(),
            "recurring_end_date": (date.today() + timedelta(days=365)).isoformat(),
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_recurring"] is True
        assert response.data["recurring_frequency"] == Transaction.MONTHLY
        assert response.data["next_occurrence"] is not None

    def test_bulk_create_transactions(self, auth_client, user, category):
        """Test bulk creating transactions."""
        url = reverse("api:transaction-bulk-create")
        data = {
            "transactions": [
                {
                    "transaction_type": Transaction.EXPENSE,
                    "amount": "25.00",
                    "category_id": category.id,
                    "description": "Transaction 1",
                    "date": date.today().isoformat(),
                },
                {
                    "transaction_type": Transaction.EXPENSE,
                    "amount": "50.00",
                    "category_id": category.id,
                    "description": "Transaction 2",
                    "date": date.today().isoformat(),
                },
            ]
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data["transactions"]) == 2
        assert Transaction.objects.filter(user=user).count() == 2

    def test_statistics_endpoint(self, auth_client, user, category):
        """Test transaction statistics endpoint."""
        # Create test transactions
        TransactionFactory(
            user=user,
            category=category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("100.00"),
            date=date.today(),
        )
        TransactionFactory(
            user=user,
            category=category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("50.00"),
            date=date.today(),
        )
        TransactionFactory(
            user=user,
            category=None,
            transaction_type=Transaction.INCOME,
            amount=Decimal("500.00"),
            date=date.today(),
        )

        url = reverse("api:transaction-statistics")
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_expenses"] == "150.00"
        assert response.data["total_income"] == "500.00"
        assert response.data["net_amount"] == "350.00"
        assert response.data["transaction_count"] == 3
