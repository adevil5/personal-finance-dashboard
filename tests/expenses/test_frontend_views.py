"""Tests for expenses frontend views."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.expenses.models import Transaction
from tests.factories import CategoryFactory, TransactionFactory, UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestTransactionListView:
    """Test suite for Transaction list frontend view."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return Client()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return UserFactory()

    @pytest.fixture
    def other_user(self):
        """Create another test user."""
        return UserFactory()

    @pytest.fixture
    def category(self, user):
        """Create test category."""
        return CategoryFactory(user=user, name="Food")

    @pytest.fixture
    def transactions(self, user, category):
        """Create test transactions."""
        transactions = []
        for i in range(5):
            transactions.append(
                TransactionFactory(
                    user=user,
                    category=category,
                    amount=Decimal(f"{10 + i * 5}.00"),
                    description=f"Transaction {i}",
                    date=date.today() - timedelta(days=i),
                )
            )
        return transactions

    def test_transaction_list_requires_authentication(self, client):
        """Test that transaction list requires authentication."""
        url = reverse("expenses:transaction-list")
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert "login" in response.url

    def test_transaction_list_displays_user_transactions(
        self, client, user, transactions
    ):
        """Test that transaction list displays user's transactions."""
        client.force_login(user)
        url = reverse("expenses:transaction-list")
        response = client.get(url)

        assert response.status_code == 200
        assert "expenses/transaction_list.html" in [t.name for t in response.templates]

        # Check that transactions appear in response
        for transaction in transactions:
            assert transaction.description in response.content.decode()
            assert str(transaction.amount) in response.content.decode()

    def test_transaction_list_user_isolation(
        self, client, user, other_user, category, transactions
    ):
        """Test that users only see their own transactions."""
        # Create transaction for other user
        other_category = CategoryFactory(user=other_user)
        other_transaction = TransactionFactory(
            user=other_user,
            category=other_category,
            description="Other user transaction",
        )

        client.force_login(user)
        url = reverse("expenses:transaction-list")
        response = client.get(url)

        assert response.status_code == 200

        # User's transactions should be visible
        assert transactions[0].description in response.content.decode()

        # Other user's transaction should not be visible
        assert other_transaction.description not in response.content.decode()

    def test_transaction_list_pagination(self, client, user, category):
        """Test pagination in transaction list."""
        # Create 25 transactions to test pagination
        for i in range(25):
            TransactionFactory(
                user=user,
                category=category,
                description=f"Transaction {i}",
                amount=Decimal(f"{i + 1}.00"),
            )

        client.force_login(user)
        url = reverse("expenses:transaction-list")
        response = client.get(url)

        assert response.status_code == 200

        # Check pagination context
        assert "page_obj" in response.context
        assert "is_paginated" in response.context

        # Should have pagination if more than page size
        page_obj = response.context["page_obj"]
        assert page_obj.has_other_pages()

    def test_transaction_list_ordering(self, client, user, category):
        """Test that transactions are ordered by date (newest first)."""
        # Create transactions with different dates
        today = date.today()
        transaction1 = TransactionFactory(
            user=user, category=category, date=today - timedelta(days=2)
        )
        transaction2 = TransactionFactory(user=user, category=category, date=today)
        transaction3 = TransactionFactory(
            user=user, category=category, date=today - timedelta(days=1)
        )

        client.force_login(user)
        url = reverse("expenses:transaction-list")
        response = client.get(url)

        assert response.status_code == 200

        transactions = response.context["transactions"]
        transaction_list = list(transactions)

        # Should be ordered by date descending (newest first)
        assert transaction_list[0].id == transaction2.id  # today
        assert transaction_list[1].id == transaction3.id  # yesterday
        assert transaction_list[2].id == transaction1.id  # 2 days ago

    def test_transaction_list_search_functionality(self, client, user, category):
        """Test search functionality in transaction list."""
        # Create transactions with specific descriptions
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

        client.force_login(user)
        url = reverse("expenses:transaction-list")

        # Test search by description
        response = client.get(url, {"search": "coffee"})
        assert response.status_code == 200
        assert transaction1.description in response.content.decode()
        assert transaction2.description not in response.content.decode()

        # Test search by merchant
        response = client.get(url, {"search": "starbucks"})
        assert response.status_code == 200
        assert transaction1.description in response.content.decode()
        assert transaction2.description not in response.content.decode()

    def test_transaction_list_category_filter(self, client, user):
        """Test filtering by category."""
        category1 = CategoryFactory(user=user, name="Food")
        category2 = CategoryFactory(user=user, name="Transport")

        transaction1 = TransactionFactory(user=user, category=category1)
        transaction2 = TransactionFactory(user=user, category=category2)

        client.force_login(user)
        url = reverse("expenses:transaction-list")

        # Filter by category 1
        response = client.get(url, {"category": category1.id})
        assert response.status_code == 200
        assert transaction1.description in response.content.decode()
        assert transaction2.description not in response.content.decode()

    def test_transaction_list_date_filter(self, client, user, category):
        """Test filtering by date range."""
        today = date.today()
        transaction1 = TransactionFactory(
            user=user, category=category, date=today - timedelta(days=5)
        )
        transaction2 = TransactionFactory(
            user=user, category=category, date=today - timedelta(days=2)
        )
        transaction3 = TransactionFactory(user=user, category=category, date=today)

        client.force_login(user)
        url = reverse("expenses:transaction-list")

        # Filter for last 3 days
        response = client.get(
            url,
            {
                "date_after": (today - timedelta(days=3)).isoformat(),
                "date_before": today.isoformat(),
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert transaction1.description not in content  # 5 days ago
        assert transaction2.description in content  # 2 days ago
        assert transaction3.description in content  # today

    def test_transaction_list_amount_filter(self, client, user, category):
        """Test filtering by amount range."""
        transaction1 = TransactionFactory(
            user=user, category=category, amount=Decimal("25.00")
        )
        transaction2 = TransactionFactory(
            user=user, category=category, amount=Decimal("50.00")
        )
        transaction3 = TransactionFactory(
            user=user, category=category, amount=Decimal("75.00")
        )

        client.force_login(user)
        url = reverse("expenses:transaction-list")

        # Filter for amounts between 40 and 60
        response = client.get(
            url,
            {
                "amount_min": "40.00",
                "amount_max": "60.00",
            },
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert transaction1.description not in content  # 25.00
        assert transaction2.description in content  # 50.00
        assert transaction3.description not in content  # 75.00

    def test_transaction_list_type_filter(self, client, user, category):
        """Test filtering by transaction type."""
        expense = TransactionFactory(
            user=user,
            category=category,
            transaction_type=Transaction.EXPENSE,
            description="Expense transaction",
        )
        income = TransactionFactory(
            user=user,
            category=None,
            transaction_type=Transaction.INCOME,
            description="Income transaction",
        )

        client.force_login(user)
        url = reverse("expenses:transaction-list")

        # Filter for expenses only
        response = client.get(url, {"transaction_type": Transaction.EXPENSE})
        assert response.status_code == 200
        content = response.content.decode()
        assert expense.description in content
        assert income.description not in content

    def test_transaction_list_context_data(self, client, user, transactions):
        """Test that proper context data is provided to template."""
        client.force_login(user)
        url = reverse("expenses:transaction-list")
        response = client.get(url)

        assert response.status_code == 200

        # Check required context variables
        context = response.context
        assert "transactions" in context
        assert "categories" in context  # For filter dropdown
        assert "search_query" in context
        assert "selected_category" in context
        assert "date_after" in context
        assert "date_before" in context
        assert "amount_min" in context
        assert "amount_max" in context
        assert "transaction_type" in context

    def test_transaction_list_empty_state(self, client, user):
        """Test transaction list with no transactions."""
        client.force_login(user)
        url = reverse("expenses:transaction-list")
        response = client.get(url)

        assert response.status_code == 200

        # Should show empty state message
        assert "No transactions found" in response.content.decode()

    def test_transaction_list_preserves_filters_in_pagination(
        self, client, user, category
    ):
        """Test that filters are preserved when paginating."""
        # Create many transactions
        for i in range(25):
            TransactionFactory(
                user=user,
                category=category,
                description=f"Test transaction {i}",
            )

        client.force_login(user)
        url = reverse("expenses:transaction-list")

        # Apply filter and go to page 2
        response = client.get(url, {"search": "Test", "page": 2})
        assert response.status_code == 200

        # Check that search parameter is preserved in pagination links
        content = response.content.decode()
        assert "search=Test" in content


@pytest.mark.django_db
class TestTransactionHTMXViews:
    """Test suite for Transaction HTMX partial views."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return Client()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return UserFactory()

    @pytest.fixture
    def category(self, user):
        """Create test category."""
        return CategoryFactory(user=user)

    @pytest.fixture
    def transaction(self, user, category):
        """Create test transaction."""
        return TransactionFactory(user=user, category=category)

    def test_transaction_row_partial_view(self, client, user, transaction):
        """Test HTMX transaction row partial view."""
        client.force_login(user)
        url = reverse("expenses:transaction-row", kwargs={"pk": transaction.id})
        response = client.get(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        assert "expenses/_transaction_row.html" in [t.name for t in response.templates]
        assert transaction.description in response.content.decode()

    def test_transaction_edit_form_partial_view(self, client, user, transaction):
        """Test HTMX transaction edit form partial view."""
        client.force_login(user)
        url = reverse("expenses:transaction-edit-form", kwargs={"pk": transaction.id})
        response = client.get(url, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        # Should return edit form for the transaction
        content = response.content.decode()
        assert "form" in content.lower()
        assert str(transaction.amount) in content

    def test_transaction_update_htmx(self, client, user, transaction):
        """Test updating transaction via HTMX."""
        client.force_login(user)
        url = reverse("expenses:transaction-update-htmx", kwargs={"pk": transaction.id})

        data = {
            "description": "Updated description",
            "amount": "75.50",
            "category": transaction.category.id,
            "transaction_type": transaction.transaction_type,
            "date": transaction.date.isoformat(),
        }

        response = client.post(url, data, HTTP_HX_REQUEST="true")

        assert response.status_code == 200

        # Verify transaction was updated
        transaction.refresh_from_db()
        assert transaction.description == "Updated description"
        assert transaction.amount == Decimal("75.50")

    def test_transaction_filter_partial_view(self, client, user, category):
        """Test HTMX filter partial view."""
        # Create some transactions
        for i in range(5):
            TransactionFactory(user=user, category=category)

        client.force_login(user)
        url = reverse("expenses:transaction-filter")
        response = client.get(url, {"category": category.id}, HTTP_HX_REQUEST="true")

        assert response.status_code == 200
        # Should return filtered transaction list
        assert len(response.context["transactions"]) == 5
