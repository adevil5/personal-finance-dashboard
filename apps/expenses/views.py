from decimal import Decimal

from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Transaction
from .serializers import TransactionSerializer, TransactionStatisticsSerializer


class TransactionFilter(filters.FilterSet):
    """Filter class for Transaction queries."""

    transaction_type = filters.ChoiceFilter(
        choices=Transaction.TRANSACTION_TYPE_CHOICES
    )
    category = filters.NumberFilter(field_name="category__id")
    date_after = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_before = filters.DateFilter(field_name="date", lookup_expr="lte")
    amount_min = filters.NumberFilter(field_name="amount_index", lookup_expr="gte")
    amount_max = filters.NumberFilter(field_name="amount_index", lookup_expr="lte")
    is_recurring = filters.BooleanFilter()

    class Meta:
        model = Transaction
        fields = [
            "transaction_type",
            "category",
            "date_after",
            "date_before",
            "amount_min",
            "amount_max",
            "is_recurring",
        ]


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Transaction CRUD operations.

    Provides endpoints for:
    - List transactions (with filtering, search, ordering, pagination)
    - Create single or bulk transactions
    - Retrieve, update, and delete transactions
    - Get transaction statistics

    All operations are scoped to the authenticated user.
    """

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = TransactionFilter
    search_fields = ["description", "merchant", "notes"]
    ordering_fields = ["date", "created_at", "amount_index"]
    ordering = ["-date", "-created_at"]  # Default ordering

    def get_queryset(self):
        """Return transactions for the current user only."""
        return Transaction.objects.filter(
            user=self.request.user, is_active=True
        ).select_related("category", "parent_transaction")

    def perform_destroy(self, instance):
        """Soft delete by setting is_active to False."""
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        """Bulk create multiple transactions."""
        created_transactions = []
        for transaction_data in request.data.get("transactions", []):
            serializer = TransactionSerializer(
                data=transaction_data, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            transaction = serializer.save()
            created_transactions.append(transaction)

        # Serialize the created transactions
        transaction_serializer = TransactionSerializer(
            created_transactions, many=True, context={"request": request}
        )

        return Response(
            {"transactions": transaction_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        Get transaction statistics for the current user.

        Accepts optional query parameters:
        - date_from: Start date for statistics
        - date_to: End date for statistics
        """
        queryset = self.get_queryset()

        # Apply date filtering if provided
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        # Calculate statistics in Python since encrypted fields can't use aggregation
        expenses = queryset.filter(transaction_type=Transaction.EXPENSE)
        income = queryset.filter(transaction_type=Transaction.INCOME)

        # Calculate totals in Python
        total_expenses = sum(expense.amount for expense in expenses) or Decimal("0")
        total_income = sum(inc.amount for inc in income) or Decimal("0")

        # Category breakdown for expenses
        category_breakdown = {}
        for expense in expenses:
            if expense.category and expense.category.name:
                category_name = expense.category.name
                if category_name not in category_breakdown:
                    category_breakdown[category_name] = Decimal("0")
                category_breakdown[category_name] += expense.amount

        # Convert to strings for JSON serialization
        for name, amount in category_breakdown.items():
            category_breakdown[name] = str(amount)

        # Prepare response data
        data = {
            "total_expenses": str(total_expenses),
            "total_income": str(total_income),
            "net_amount": str(total_income - total_expenses),
            "transaction_count": queryset.count(),
            "expense_count": expenses.count(),
            "income_count": income.count(),
            "category_breakdown": category_breakdown,
        }

        if date_from:
            data["date_from"] = date_from
        if date_to:
            data["date_to"] = date_to

        serializer = TransactionStatisticsSerializer(data)
        return Response(serializer.data)
