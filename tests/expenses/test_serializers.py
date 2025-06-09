from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIRequestFactory

from django.contrib.auth import get_user_model

from apps.expenses.models import Transaction
from apps.expenses.serializers import (
    CategorySerializer,
    TransactionBulkCreateSerializer,
    TransactionSerializer,
    TransactionStatisticsSerializer,
)
from tests.factories import CategoryFactory, TransactionFactory, UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestCategorySerializer:
    """Test suite for CategorySerializer."""

    def test_serialize_category(self):
        """Test serializing a category."""
        user = UserFactory()
        category = CategoryFactory(
            user=user,
            name="Food",
            color="#FF5733",
            icon="food-icon",
        )

        serializer = CategorySerializer(category)
        data = serializer.data

        assert data["id"] == category.id
        assert data["name"] == "Food"
        assert data["color"] == "#FF5733"
        assert data["icon"] == "food-icon"
        assert data["parent"] is None
        assert data["is_active"] is True
        assert "created_at" in data
        assert "updated_at" in data

    def test_serialize_category_with_parent(self):
        """Test serializing a category with parent."""
        user = UserFactory()
        parent = CategoryFactory(user=user, name="Food")
        category = CategoryFactory(user=user, name="Restaurants", parent=parent)

        serializer = CategorySerializer(category)
        data = serializer.data

        assert data["parent"] == parent.id

    def test_deserialize_category(self):
        """Test deserializing category data."""
        user = UserFactory()
        request = APIRequestFactory().post("/")
        request.user = user

        data = {
            "name": "Entertainment",
            "color": "#123456",
            "icon": "movie-icon",
        }

        serializer = CategorySerializer(data=data, context={"request": request})
        assert serializer.is_valid()

        category = serializer.save(user=user)
        assert category.name == "Entertainment"
        assert category.color == "#123456"
        assert category.icon == "movie-icon"
        assert category.user == user

    def test_validate_parent_different_user_fails(self):
        """Test that parent category must belong to same user."""
        user1 = UserFactory()
        user2 = UserFactory()
        parent = CategoryFactory(user=user1)

        request = APIRequestFactory().post("/")
        request.user = user2

        data = {
            "name": "Subcategory",
            "parent": parent.id,
        }

        serializer = CategorySerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "parent" in serializer.errors


@pytest.mark.django_db
class TestTransactionSerializer:
    """Test suite for TransactionSerializer."""

    @pytest.fixture
    def request_factory(self):
        """Create request factory."""
        return APIRequestFactory()

    def test_serialize_transaction_with_all_fields(self):
        """Test serializing a transaction with all fields."""
        user = UserFactory()
        category = CategoryFactory(user=user, name="Food")
        transaction = TransactionFactory(
            user=user,
            category=category,
            transaction_type=Transaction.EXPENSE,
            amount=Decimal("123.45"),
            description="Grocery shopping",
            merchant="Whole Foods",
            notes="Weekly groceries",
            date=date(2025, 1, 1),
        )

        serializer = TransactionSerializer(transaction)
        data = serializer.data

        assert data["id"] == transaction.id
        assert data["transaction_type"] == Transaction.EXPENSE
        assert data["amount"] == "123.45"
        assert data["description"] == "Grocery shopping"
        assert data["merchant"] == "Whole Foods"
        assert data["notes"] == "Weekly groceries"
        assert data["date"] == "2025-01-01"
        assert data["is_recurring"] is False
        assert data["is_active"] is True

        # Check nested category
        assert data["category"]["id"] == category.id
        assert data["category"]["name"] == "Food"

    def test_serialize_income_transaction_without_category(self):
        """Test serializing income transaction without category."""
        user = UserFactory()
        transaction = TransactionFactory(
            user=user,
            category=None,
            transaction_type=Transaction.INCOME,
            amount=Decimal("5000.00"),
            description="Salary",
        )

        serializer = TransactionSerializer(transaction)
        data = serializer.data

        assert data["transaction_type"] == Transaction.INCOME
        assert data["amount"] == "5000.00"
        assert data["category"] is None

    def test_serialize_recurring_transaction(self):
        """Test serializing recurring transaction."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        transaction = TransactionFactory(
            user=user,
            category=category,
            is_recurring=True,
            recurring_frequency=Transaction.MONTHLY,
            recurring_interval=1,
            recurring_start_date=date(2025, 1, 1),
            recurring_end_date=date(2025, 12, 31),
        )

        serializer = TransactionSerializer(transaction)
        data = serializer.data

        assert data["is_recurring"] is True
        assert data["recurring_frequency"] == Transaction.MONTHLY
        assert data["recurring_interval"] == 1
        assert data["recurring_start_date"] == "2025-01-01"
        assert data["recurring_end_date"] == "2025-12-31"
        assert data["next_occurrence"] is not None

    def test_deserialize_expense_transaction(self, request_factory):
        """Test deserializing expense transaction data."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "99.99",
            "category_id": category.id,
            "description": "Test expense",
            "date": date.today().isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert serializer.is_valid()

        transaction = serializer.save()
        assert transaction.user == user
        assert transaction.amount == Decimal("99.99")
        assert transaction.category == category

    def test_deserialize_with_invalid_decimal_formats(self, request_factory):
        """Test deserializing with various decimal formats."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        # Test valid formats
        valid_amounts = ["100", "100.0", "100.00", "0.01", "9999.99"]
        for amount in valid_amounts:
            data = {
                "transaction_type": Transaction.EXPENSE,
                "amount": amount,
                "category_id": category.id,
                "description": "Test",
                "date": date.today().isoformat(),
            }
            serializer = TransactionSerializer(data=data, context={"request": request})
            assert serializer.is_valid(), f"Amount {amount} should be valid"

        # Test invalid formats
        invalid_amounts = ["abc", "12.345", "100000000.00", "-50", "0", "0.00"]
        for amount in invalid_amounts:
            data = {
                "transaction_type": Transaction.EXPENSE,
                "amount": amount,
                "category_id": category.id,
                "description": "Test",
                "date": date.today().isoformat(),
            }
            serializer = TransactionSerializer(data=data, context={"request": request})
            assert not serializer.is_valid(), f"Amount {amount} should be invalid"

    def test_category_queryset_filtered_by_user(self, request_factory):
        """Test that category queryset is filtered by user."""
        user1 = UserFactory()
        user2 = UserFactory()
        category1 = CategoryFactory(user=user1)
        category2 = CategoryFactory(user=user2)

        request = request_factory.post("/")
        request.user = user1

        serializer = TransactionSerializer(context={"request": request})
        queryset = serializer.fields["category_id"].queryset

        assert category1 in queryset
        assert category2 not in queryset

    def test_validate_expense_without_category_fails(self, request_factory):
        """Test that expense transactions require a category."""
        user = UserFactory()
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "description": "Test expense",
            "date": date.today().isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "category" in serializer.errors

    def test_validate_income_without_category_succeeds(self, request_factory):
        """Test that income transactions don't require a category."""
        user = UserFactory()
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.INCOME,
            "amount": "1000.00",
            "description": "Salary",
            "date": date.today().isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert serializer.is_valid()

    def test_validate_future_date_fails(self, request_factory):
        """Test that future dates are not allowed."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        future_date = date.today() + timedelta(days=1)
        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Future expense",
            "date": future_date.isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "date" in serializer.errors

    def test_validate_negative_amount_fails(self, request_factory):
        """Test that negative amounts are not allowed."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "-50.00",
            "category_id": category.id,
            "description": "Test",
            "date": date.today().isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "amount" in serializer.errors

    def test_validate_zero_amount_fails(self, request_factory):
        """Test that zero amounts are not allowed."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "0.00",
            "category_id": category.id,
            "description": "Test",
            "date": date.today().isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "amount" in serializer.errors

    def test_validate_recurring_without_frequency_fails(self, request_factory):
        """Test that recurring transactions require frequency."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Recurring expense",
            "date": date.today().isoformat(),
            "is_recurring": True,
            "recurring_interval": 1,
            "recurring_start_date": date.today().isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "recurring_frequency" in serializer.errors

    def test_validate_recurring_without_interval_fails(self, request_factory):
        """Test that recurring transactions require interval."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Recurring expense",
            "date": date.today().isoformat(),
            "is_recurring": True,
            "recurring_frequency": Transaction.MONTHLY,
            "recurring_start_date": date.today().isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "recurring_interval" in serializer.errors

    def test_validate_recurring_negative_interval_fails(self, request_factory):
        """Test that recurring interval must be positive."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Recurring expense",
            "date": date.today().isoformat(),
            "is_recurring": True,
            "recurring_frequency": Transaction.MONTHLY,
            "recurring_interval": -1,
            "recurring_start_date": date.today().isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "recurring_interval" in serializer.errors

    def test_validate_recurring_without_start_date_fails(self, request_factory):
        """Test that recurring transactions require start date."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Recurring expense",
            "date": date.today().isoformat(),
            "is_recurring": True,
            "recurring_frequency": Transaction.MONTHLY,
            "recurring_interval": 1,
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "recurring_start_date" in serializer.errors

    def test_validate_recurring_end_before_start_fails(self, request_factory):
        """Test that recurring end date must be after start date."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Recurring expense",
            "date": date.today().isoformat(),
            "is_recurring": True,
            "recurring_frequency": Transaction.MONTHLY,
            "recurring_interval": 1,
            "recurring_start_date": date.today().isoformat(),
            "recurring_end_date": (date.today() - timedelta(days=1)).isoformat(),
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert not serializer.is_valid()
        assert "recurring_end_date" in serializer.errors

    def test_update_transaction(self, request_factory):
        """Test updating a transaction."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        transaction = TransactionFactory(
            user=user,
            category=category,
            amount=Decimal("50.00"),
            description="Original",
        )

        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": transaction.transaction_type,
            "amount": "75.00",
            "category_id": category.id,
            "description": "Updated",
            "date": transaction.date.isoformat(),
        }

        serializer = TransactionSerializer(
            transaction,
            data=data,
            context={"request": request},
        )
        assert serializer.is_valid()

        updated = serializer.save()
        assert updated.amount == Decimal("75.00")
        assert updated.description == "Updated"

    def test_partial_update_transaction(self, request_factory):
        """Test partial update of a transaction."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        transaction = TransactionFactory(
            user=user,
            category=category,
            amount=Decimal("50.00"),
            description="Original",
        )

        request = request_factory.post("/")
        request.user = user

        data = {"description": "Partially updated"}

        serializer = TransactionSerializer(
            transaction,
            data=data,
            partial=True,
            context={"request": request},
        )
        assert serializer.is_valid()

        updated = serializer.save()
        assert updated.description == "Partially updated"
        assert updated.amount == Decimal("50.00")  # Unchanged

    def test_read_only_fields_ignored_on_create(self, request_factory):
        """Test that read-only fields are ignored on create."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = request_factory.post("/")
        request.user = user

        data = {
            "transaction_type": Transaction.EXPENSE,
            "amount": "50.00",
            "category_id": category.id,
            "description": "Test",
            "date": date.today().isoformat(),
            "created_at": "2020-01-01T00:00:00Z",  # Should be ignored
            "updated_at": "2020-01-01T00:00:00Z",  # Should be ignored
            "next_occurrence": date.today().isoformat(),  # Should be ignored
        }

        serializer = TransactionSerializer(data=data, context={"request": request})
        assert serializer.is_valid()

        transaction = serializer.save()
        assert transaction.created_at.date() == date.today()
        assert transaction.updated_at.date() == date.today()

    def test_currency_formatting(self):
        """Test that amounts are formatted with currency."""
        user = UserFactory(currency="USD")
        category = CategoryFactory(user=user)
        transaction = TransactionFactory(
            user=user,
            category=category,
            amount=Decimal("1234.56"),
        )

        serializer = TransactionSerializer(transaction)
        data = serializer.data

        assert data["amount"] == "1234.56"
        assert data["formatted_amount"] == "$1,234.56"

    def test_currency_formatting_different_currencies(self):
        """Test currency formatting with different currencies."""
        # Test EUR
        user_eur = UserFactory(currency="EUR")
        category_eur = CategoryFactory(user=user_eur)
        transaction_eur = TransactionFactory(
            user=user_eur,
            category=category_eur,
            amount=Decimal("999.99"),
        )

        serializer = TransactionSerializer(transaction_eur)
        data = serializer.data
        assert data["formatted_amount"] == "€999.99"

        # Test GBP
        user_gbp = UserFactory(currency="GBP")
        category_gbp = CategoryFactory(user=user_gbp)
        transaction_gbp = TransactionFactory(
            user=user_gbp,
            category=category_gbp,
            amount=Decimal("1500.00"),
        )

        serializer = TransactionSerializer(transaction_gbp)
        data = serializer.data
        assert data["formatted_amount"] == "£1,500.00"

    def test_currency_formatting_large_amounts(self):
        """Test currency formatting with large amounts."""
        user = UserFactory(currency="USD")
        category = CategoryFactory(user=user)
        transaction = TransactionFactory(
            user=user,
            category=category,
            amount=Decimal("1234567.89"),
        )

        serializer = TransactionSerializer(transaction)
        data = serializer.data
        assert data["formatted_amount"] == "$1,234,567.89"


@pytest.mark.django_db
class TestTransactionBulkCreateSerializer:
    """Test suite for TransactionBulkCreateSerializer."""

    def test_bulk_create_transactions(self):
        """Test bulk creating transactions."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = APIRequestFactory().post("/")
        request.user = user

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
                {
                    "transaction_type": Transaction.INCOME,
                    "amount": "100.00",
                    "description": "Income transaction",
                    "date": date.today().isoformat(),
                },
            ]
        }

        serializer = TransactionBulkCreateSerializer(
            data=data,
            context={"request": request},
        )
        assert serializer.is_valid()

        result = serializer.save()
        transactions = result["transactions"]

        assert len(transactions) == 3
        assert all(t.user == user for t in transactions)
        assert transactions[0].amount == Decimal("25.00")
        assert transactions[1].amount == Decimal("50.00")
        assert transactions[2].amount == Decimal("100.00")

    def test_bulk_create_with_invalid_transaction_fails(self):
        """Test that bulk create fails if any transaction is invalid."""
        user = UserFactory()
        category = CategoryFactory(user=user)
        request = APIRequestFactory().post("/")
        request.user = user

        data = {
            "transactions": [
                {
                    "transaction_type": Transaction.EXPENSE,
                    "amount": "25.00",
                    "category_id": category.id,
                    "description": "Valid transaction",
                    "date": date.today().isoformat(),
                },
                {
                    "transaction_type": Transaction.EXPENSE,
                    "amount": "-50.00",  # Invalid negative amount
                    "category_id": category.id,
                    "description": "Invalid transaction",
                    "date": date.today().isoformat(),
                },
            ]
        }

        serializer = TransactionBulkCreateSerializer(
            data=data,
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "transactions" in serializer.errors

    def test_bulk_create_empty_list_fails(self):
        """Test that bulk create with empty list fails."""
        user = UserFactory()
        request = APIRequestFactory().post("/")
        request.user = user

        data = {"transactions": []}

        serializer = TransactionBulkCreateSerializer(
            data=data,
            context={"request": request},
        )
        assert not serializer.is_valid()


@pytest.mark.django_db
class TestTransactionStatisticsSerializer:
    """Test suite for TransactionStatisticsSerializer."""

    def test_serialize_statistics(self):
        """Test serializing transaction statistics."""
        data = {
            "total_expenses": Decimal("1500.00"),
            "total_income": Decimal("3000.00"),
            "net_amount": Decimal("1500.00"),
            "transaction_count": 25,
            "expense_count": 20,
            "income_count": 5,
            "category_breakdown": {
                "Food": Decimal("500.00"),
                "Transport": Decimal("300.00"),
                "Entertainment": Decimal("200.00"),
            },
            "date_from": date(2025, 1, 1),
            "date_to": date(2025, 1, 31),
        }

        serializer = TransactionStatisticsSerializer(data)
        serialized = serializer.data

        assert serialized["total_expenses"] == "1500.00"
        assert serialized["total_income"] == "3000.00"
        assert serialized["net_amount"] == "1500.00"
        assert serialized["transaction_count"] == 25
        assert serialized["expense_count"] == 20
        assert serialized["income_count"] == 5
        assert serialized["category_breakdown"]["Food"] == "500.00"
        assert serialized["date_from"] == "2025-01-01"
        assert serialized["date_to"] == "2025-01-31"

    def test_serialize_statistics_without_dates(self):
        """Test serializing statistics without date range."""
        data = {
            "total_expenses": Decimal("1000.00"),
            "total_income": Decimal("2000.00"),
            "net_amount": Decimal("1000.00"),
            "transaction_count": 10,
            "expense_count": 7,
            "income_count": 3,
            "category_breakdown": {},
        }

        serializer = TransactionStatisticsSerializer(data)
        serialized = serializer.data

        assert "date_from" not in serialized
        assert "date_to" not in serialized

    def test_deserialize_statistics(self):
        """Test deserializing statistics data."""
        data = {
            "total_expenses": "500.50",
            "total_income": "1000.00",
            "net_amount": "499.50",
            "transaction_count": 15,
            "expense_count": 10,
            "income_count": 5,
            "category_breakdown": {
                "Food": "200.50",
                "Transport": "300.00",
            },
        }

        serializer = TransactionStatisticsSerializer(data=data)
        assert serializer.is_valid()

        validated = serializer.validated_data
        assert validated["total_expenses"] == Decimal("500.50")
        assert validated["category_breakdown"]["Food"] == Decimal("200.50")
