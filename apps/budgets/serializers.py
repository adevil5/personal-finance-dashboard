from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.expenses.models import Category

from .models import Budget, BudgetAlert

User = get_user_model()


class BudgetAlertSerializer(serializers.ModelSerializer):
    """Serializer for BudgetAlert model."""

    class Meta:
        model = BudgetAlert
        fields = [
            "id",
            "alert_type",
            "message",
            "triggered_at_percentage",
            "is_resolved",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = [
            "triggered_at_percentage",
            "created_at",
        ]


class BudgetSerializer(serializers.ModelSerializer):
    """Serializer for Budget model."""

    category = serializers.SerializerMethodField()
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.none(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    formatted_amount = serializers.SerializerMethodField()

    # Calculated fields (read-only)
    spent_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()
    utilization_percentage = serializers.SerializerMethodField()
    is_over_budget = serializers.SerializerMethodField()
    active_alerts = BudgetAlertSerializer(many=True, read_only=True, source="alerts")

    class Meta:
        model = Budget
        fields = [
            "id",
            "name",
            "amount",
            "formatted_amount",
            "category",
            "category_id",
            "period_start",
            "period_end",
            "spent_amount",
            "remaining_amount",
            "utilization_percentage",
            "is_over_budget",
            "alert_enabled",
            "warning_threshold",
            "critical_threshold",
            "active_alerts",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "spent_amount",
            "remaining_amount",
            "utilization_percentage",
            "is_over_budget",
            "active_alerts",
        ]

    def __init__(self, *args, **kwargs):
        """Initialize the serializer and set up the category queryset."""
        super().__init__(*args, **kwargs)

        # Set the category queryset to user's categories only
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            self.fields["category_id"].queryset = Category.objects.filter(
                user=request.user,
                is_active=True,
            )

    def get_category(self, obj):
        """Get the category details."""
        if not obj.category:
            return None

        return {
            "id": obj.category.id,
            "name": obj.category.name,
            "color": obj.category.color,
            "icon": obj.category.icon,
        }

    def get_formatted_amount(self, obj):
        """Format the amount with currency symbol."""
        # Get user's currency preference
        currency = getattr(obj.user, "currency", "USD")

        # Simple currency formatting (can be enhanced with proper i18n)
        currency_symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
        }
        symbol = currency_symbols.get(currency, "$")

        return f"{symbol}{obj.amount:,.2f}"

    def get_spent_amount(self, obj):
        """Get the spent amount for this budget."""
        return str(obj.calculate_spent_amount())

    def get_remaining_amount(self, obj):
        """Get the remaining amount for this budget."""
        return str(obj.calculate_remaining_amount())

    def get_utilization_percentage(self, obj):
        """Get the utilization percentage."""
        return str(obj.calculate_utilization_percentage())

    def get_is_over_budget(self, obj):
        """Check if budget is exceeded."""
        return obj.is_over_budget()

    def validate_amount(self, value):
        """Validate that amount has at most 2 decimal places."""
        if value.as_tuple().exponent < -2:
            raise serializers.ValidationError(
                "Amount cannot have more than 2 decimal places."
            )
        return value

    def validate(self, attrs):
        """Validate the budget data."""
        # Validate period dates
        period_start = attrs.get(
            "period_start", self.instance.period_start if self.instance else None
        )
        period_end = attrs.get(
            "period_end", self.instance.period_end if self.instance else None
        )

        if period_start and period_end and period_end <= period_start:
            raise serializers.ValidationError(
                {"period_end": "End date must be after start date."}
            )

        # Validate alert thresholds
        warning_threshold = attrs.get("warning_threshold")
        critical_threshold = attrs.get("critical_threshold")

        if warning_threshold is not None and critical_threshold is not None:
            if warning_threshold > critical_threshold:
                raise serializers.ValidationError(
                    {
                        "warning_threshold": (
                            "Warning threshold cannot be greater than "
                            "critical threshold."
                        )
                    }
                )

        return attrs

    def create(self, validated_data):
        """Create a new budget."""
        # Set the user from the request context
        validated_data["user"] = self.context["request"].user

        try:
            return super().create(validated_data)
        except ValidationError as e:
            # Convert model validation errors to serializer validation errors
            error_dict = {}
            for field, errors in e.message_dict.items():
                if field == "__all__":
                    # For non-field errors, check if it's a duplicate budget error
                    for error in errors:
                        if "already exists for this period" in str(error):
                            raise serializers.ValidationError(
                                {
                                    "non_field_errors": [
                                        "A budget already exists for this "
                                        "category and period."
                                    ]
                                }
                            )
                error_dict[field] = errors
            raise serializers.ValidationError(error_dict)


class BudgetStatisticsSerializer(serializers.Serializer):
    """Serializer for budget statistics."""

    total_budget = serializers.CharField()
    total_spent = serializers.CharField()
    total_remaining = serializers.CharField()
    overall_utilization_percentage = serializers.CharField()
    budget_count = serializers.IntegerField()
    over_budget_count = serializers.IntegerField()
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
