from datetime import date

from rest_framework import serializers

from django.contrib.auth import get_user_model

from .models import Category, Transaction

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "parent",
            "color",
            "icon",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_parent(self, value):
        """Ensure parent category belongs to the same user."""
        if value and value.user != self.context["request"].user:
            raise serializers.ValidationError(
                "Parent category must belong to the same user."
            )
        return value


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.none(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    formatted_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_type",
            "amount",
            "formatted_amount",
            "category",
            "category_id",
            "description",
            "notes",
            "merchant",
            "date",
            "receipt",
            "is_recurring",
            "recurring_frequency",
            "recurring_interval",
            "recurring_start_date",
            "recurring_end_date",
            "next_occurrence",
            "parent_transaction",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "next_occurrence",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        """Initialize serializer with user-specific querysets."""
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            self.fields["category_id"].queryset = Category.objects.filter(
                user=request.user, is_active=True
            )
            self.fields["parent_transaction"].queryset = Transaction.objects.filter(
                user=request.user
            )

    def validate_amount(self, value):
        """Validate amount field."""
        # Check if the string representation has more than 2 decimal places
        str_value = str(value)
        if "." in str_value:
            decimal_part = str_value.split(".")[1]
            # Remove trailing zeros to handle cases like "10.100"
            decimal_part = decimal_part.rstrip("0")
            if len(decimal_part) > 2:
                raise serializers.ValidationError(
                    "Amount must have no more than 2 decimal places."
                )
        return value

    def validate(self, data):
        """Validate transaction data."""
        # Validate expense transactions require a category
        if data.get("transaction_type") == Transaction.EXPENSE and not data.get(
            "category"
        ):
            raise serializers.ValidationError(
                {"category": "Expense transactions must have a category."}
            )

        # Validate date is not in the future (except for generated recurring
        # transactions)
        transaction_date = data.get("date")
        if (
            transaction_date
            and transaction_date > date.today()
            and not data.get("parent_transaction")
        ):
            raise serializers.ValidationError(
                {"date": "Transaction date cannot be in the future."}
            )

        # Validate amount is positive
        amount = data.get("amount")
        if amount is not None and amount <= 0:
            raise serializers.ValidationError(
                {"amount": "Amount must be greater than zero."}
            )

        # Validate recurring transaction fields
        if data.get("is_recurring"):
            if not data.get("recurring_frequency"):
                raise serializers.ValidationError(
                    {
                        "recurring_frequency": (
                            "Recurring transactions must have a frequency."
                        )
                    }
                )

            interval = data.get("recurring_interval")
            if not interval or interval <= 0:
                raise serializers.ValidationError(
                    {
                        "recurring_interval": (
                            "Recurring transactions must have a positive interval."
                        )
                    }
                )

            if not data.get("recurring_start_date"):
                raise serializers.ValidationError(
                    {
                        "recurring_start_date": (
                            "Recurring transactions must have a start date."
                        )
                    }
                )

            end_date = data.get("recurring_end_date")
            start_date = data.get("recurring_start_date")
            if end_date and start_date and end_date <= start_date:
                raise serializers.ValidationError(
                    {
                        "recurring_end_date": (
                            "Recurring end date must be after start date."
                        )
                    }
                )

        return data

    def get_formatted_amount(self, obj):
        """Return formatted amount with currency symbol."""
        if obj.amount is None:
            return None

        # Currency symbols mapping
        currency_symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CNY": "¥",
            "CHF": "Fr.",
            "CAD": "C$",
            "AUD": "A$",
            "INR": "₹",
        }

        # Get user's currency preference (default to USD)
        currency = obj.user.currency if hasattr(obj.user, "currency") else "USD"
        symbol = currency_symbols.get(currency, "$")

        # Format amount with thousands separator
        amount_str = f"{obj.amount:,.2f}"

        # Return formatted amount with symbol
        return f"{symbol}{amount_str}"

    def create(self, validated_data):
        """Create transaction with current user."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class TransactionBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating transactions."""

    transactions = serializers.ListField(
        child=TransactionSerializer(),
        allow_empty=False,
    )

    def __init__(self, *args, **kwargs):
        """Initialize with context passed to child serializers."""
        super().__init__(*args, **kwargs)
        # Pass context to the nested serializer
        request = self.context.get("request") if self.context else None
        if request:
            self.fields["transactions"].child = TransactionSerializer(
                context=self.context
            )

    def create(self, validated_data):
        """Create transactions one by one to ensure proper validation."""
        transactions_data = validated_data["transactions"]
        user = self.context["request"].user

        created_transactions = []
        for transaction_data in transactions_data:
            transaction_data["user"] = user
            transaction = Transaction.objects.create(**transaction_data)
            created_transactions.append(transaction)

        return {"transactions": created_transactions}


class TransactionStatisticsSerializer(serializers.Serializer):
    """Serializer for transaction statistics."""

    total_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    transaction_count = serializers.IntegerField()
    expense_count = serializers.IntegerField()
    income_count = serializers.IntegerField()
    category_breakdown = serializers.DictField(
        child=serializers.DecimalField(max_digits=10, decimal_places=2)
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
