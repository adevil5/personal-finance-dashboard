from datetime import date
from decimal import Decimal

from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Budget
from .serializers import BudgetSerializer, BudgetStatisticsSerializer


class BudgetFilter(filters.FilterSet):
    """Filter class for Budget queries."""

    category = filters.NumberFilter(field_name="category__id")
    period_start_after = filters.DateFilter(
        field_name="period_start", lookup_expr="gte"
    )
    period_start_before = filters.DateFilter(
        field_name="period_start", lookup_expr="lte"
    )
    period_end_after = filters.DateFilter(field_name="period_end", lookup_expr="gte")
    period_end_before = filters.DateFilter(field_name="period_end", lookup_expr="lte")
    alert_enabled = filters.BooleanFilter()

    class Meta:
        model = Budget
        fields = [
            "category",
            "period_start_after",
            "period_start_before",
            "period_end_after",
            "period_end_before",
            "alert_enabled",
        ]


class BudgetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Budget CRUD operations.

    Provides endpoints for:
    - List budgets (with filtering, ordering, pagination)
    - Create single budgets
    - Retrieve, update, and delete budgets
    - Get budget statistics
    - Get current period budgets

    All operations are scoped to the authenticated user.
    """

    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = BudgetFilter
    ordering_fields = [
        "period_start",
        "period_end",
        "name",
        "amount_index",
        "created_at",
    ]
    ordering = ["-period_start", "name"]  # Default ordering

    def get_queryset(self):
        """Return budgets for the current user only."""
        return (
            Budget.objects.filter(user=self.request.user, is_active=True)
            .select_related("category")
            .prefetch_related("alerts")
        )

    def perform_destroy(self, instance):
        """Soft delete by setting is_active to False."""
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        Get budget statistics for the current user.

        Accepts optional query parameters:
        - period_start: Start date for statistics
        - period_end: End date for statistics
        """
        queryset = self.get_queryset()

        # Apply period filtering if provided
        period_start = request.query_params.get("period_start")
        period_end = request.query_params.get("period_end")

        if period_start:
            queryset = queryset.filter(period_end__gte=period_start)
        if period_end:
            queryset = queryset.filter(period_start__lte=period_end)

        # Calculate statistics
        total_budget = Decimal("0")
        total_spent = Decimal("0")
        over_budget_count = 0

        for budget in queryset:
            total_budget += budget.amount
            spent = budget.calculate_spent_amount()
            total_spent += spent

            if spent > budget.amount:
                over_budget_count += 1

        total_remaining = total_budget - total_spent

        # Calculate overall utilization percentage
        if total_budget > 0:
            overall_utilization = (total_spent / total_budget) * Decimal("100")
            overall_utilization = overall_utilization.quantize(Decimal("0.01"))
        else:
            overall_utilization = Decimal("0")

        # Prepare response data
        data = {
            "total_budget": str(total_budget),
            "total_spent": str(total_spent),
            "total_remaining": str(total_remaining),
            "overall_utilization_percentage": str(overall_utilization),
            "budget_count": queryset.count(),
            "over_budget_count": over_budget_count,
        }

        if period_start:
            data["period_start"] = period_start
        if period_end:
            data["period_end"] = period_end

        serializer = BudgetStatisticsSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def current(self, request):
        """
        Get budgets for the current period.

        Returns budgets that are active for today's date.
        """
        current_date = request.query_params.get("date", date.today())
        if isinstance(current_date, str):
            current_date = date.fromisoformat(current_date)

        budgets = Budget.get_current_budgets(self.request.user, current_date)
        serializer = self.get_serializer(budgets, many=True)
        return Response(serializer.data)
