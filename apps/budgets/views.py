from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django_filters import rest_framework as filters
from rest_framework import status, viewsets
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

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """
        Get enhanced budget analytics with trend analysis.

        Query parameters:
        - period_start: Start date for analysis
        - period_end: End date for analysis
        - compare_previous: Whether to include previous period comparison
        - category_breakdown: Whether to include category-wise breakdown
        """
        queryset = self.get_queryset()

        # Apply period filtering
        period_start = request.query_params.get("period_start")
        period_end = request.query_params.get("period_end")
        compare_previous = (
            request.query_params.get("compare_previous", "false").lower() == "true"
        )
        category_breakdown = (
            request.query_params.get("category_breakdown", "false").lower() == "true"
        )

        if period_start:
            queryset = queryset.filter(period_end__gte=period_start)
        if period_end:
            queryset = queryset.filter(period_start__lte=period_end)

        # Calculate current period analytics
        current_analytics = self._calculate_period_analytics(queryset)

        response_data = {
            "current_period": current_analytics,
        }

        # Add period dates if provided
        if period_start:
            response_data["current_period"]["period_start"] = period_start
        if period_end:
            response_data["current_period"]["period_end"] = period_end

        # Calculate previous period comparison if requested
        if compare_previous and period_start and period_end:
            previous_analytics = self._calculate_previous_period_analytics(
                period_start, period_end
            )
            response_data["previous_period"] = previous_analytics
            response_data["comparison"] = self._calculate_period_comparison(
                current_analytics, previous_analytics
            )

        # Add category breakdown if requested
        if category_breakdown:
            response_data["category_breakdown"] = self._calculate_category_breakdown(
                queryset
            )

        return Response(response_data)

    @action(detail=False, methods=["get"])
    def performance(self, request):
        """
        Get budget performance metrics.

        Query parameters:
        - period_start: Start date for analysis
        - period_end: End date for analysis
        - performance_threshold: Threshold for good performance (default: 80%)
        """
        queryset = self.get_queryset()

        # Apply period filtering
        period_start = request.query_params.get("period_start")
        period_end = request.query_params.get("period_end")
        performance_threshold = Decimal(
            request.query_params.get("performance_threshold", "80.00")
        )

        if period_start:
            queryset = queryset.filter(period_end__gte=period_start)
        if period_end:
            queryset = queryset.filter(period_start__lte=period_end)

        # Calculate performance metrics
        total_budgets = queryset.count()
        if total_budgets == 0:
            return Response(
                {
                    "total_budgets": 0,
                    "performance_summary": {
                        "excellent": 0,
                        "good": 0,
                        "warning": 0,
                        "over_budget": 0,
                    },
                    "performance_details": [],
                    "average_utilization": "0.00",
                    "best_performers": [],
                    "worst_performers": [],
                }
            )

        performance_details = []
        utilization_sum = Decimal("0")
        excellent_count = 0
        good_count = 0
        warning_count = 0
        over_budget_count = 0

        for budget in queryset:
            utilization = budget.calculate_utilization_percentage()
            utilization_sum += utilization

            # Categorize performance
            if utilization <= performance_threshold * Decimal(
                "0.75"
            ):  # <= 60% for 80% threshold
                performance_category = "excellent"
                excellent_count += 1
            elif utilization <= performance_threshold:  # <= 80%
                performance_category = "good"
                good_count += 1
            elif utilization <= Decimal("100.00"):  # 80-100%
                performance_category = "warning"
                warning_count += 1
            else:  # > 100%
                performance_category = "over_budget"
                over_budget_count += 1

            performance_details.append(
                {
                    "budget_id": budget.id,
                    "budget_name": budget.name,
                    "category": budget.category.name if budget.category else "Overall",
                    "amount": str(budget.amount),
                    "spent_amount": str(budget.calculate_spent_amount()),
                    "utilization_percentage": str(utilization),
                    "performance_category": performance_category,
                    "is_over_budget": budget.is_over_budget(),
                }
            )

        # Sort by utilization for best/worst performers
        sorted_details = sorted(
            performance_details, key=lambda x: Decimal(x["utilization_percentage"])
        )

        response_data = {
            "total_budgets": total_budgets,
            "performance_summary": {
                "excellent": excellent_count,
                "good": good_count,
                "warning": warning_count,
                "over_budget": over_budget_count,
            },
            "performance_details": performance_details,
            "average_utilization": str(
                (utilization_sum / total_budgets).quantize(Decimal("0.01"))
            ),
            "best_performers": sorted_details[:3],  # Top 3 lowest utilization
            "worst_performers": sorted_details[-3:][
                ::-1
            ],  # Top 3 highest utilization, reversed
        }

        if period_start:
            response_data["period_start"] = period_start
        if period_end:
            response_data["period_end"] = period_end

        return Response(response_data)

    @action(detail=False, methods=["get"])
    def trends(self, request):
        """
        Get budget trend analysis over multiple periods.

        Query parameters:
        - months: Number of months to analyze (default: 6)
        - category_id: Optional category filter
        """
        months = int(request.query_params.get("months", 6))
        category_id = request.query_params.get("category_id")

        if months > 24:  # Limit to 2 years max
            return Response(
                {"error": "Maximum 24 months allowed for trend analysis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculate date ranges for each month
        today = date.today()
        trend_data = []

        for i in range(months):
            # Calculate month start/end dates
            if today.month - i <= 0:
                year = today.year - 1
                month = 12 + (today.month - i)
            else:
                year = today.year
                month = today.month - i

            month_start = date(year, month, 1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(
                days=1
            )

            # Get budgets for this period
            period_queryset = Budget.objects.filter(
                user=self.request.user,
                is_active=True,
                period_start__lte=month_end,
                period_end__gte=month_start,
            ).select_related("category")

            if category_id:
                period_queryset = period_queryset.filter(category_id=category_id)

            # Calculate metrics for this period
            period_metrics = self._calculate_period_analytics(period_queryset)
            period_metrics.update(
                {
                    "period_start": str(month_start),
                    "period_end": str(month_end),
                    "period_label": f"{month_start.strftime('%B %Y')}",
                }
            )

            trend_data.append(period_metrics)

        # Reverse to get chronological order (oldest to newest)
        trend_data.reverse()

        # Calculate trend indicators
        if len(trend_data) >= 2:
            latest = trend_data[-1]
            previous = trend_data[-2]

            trend_indicators = {
                "budget_growth": self._calculate_percentage_change(
                    Decimal(previous["total_budget"]), Decimal(latest["total_budget"])
                ),
                "spending_growth": self._calculate_percentage_change(
                    Decimal(previous["total_spent"]), Decimal(latest["total_spent"])
                ),
                "utilization_change": self._calculate_percentage_change(
                    Decimal(previous["overall_utilization_percentage"]),
                    Decimal(latest["overall_utilization_percentage"]),
                ),
            }
        else:
            trend_indicators = {
                "budget_growth": "0.00",
                "spending_growth": "0.00",
                "utilization_change": "0.00",
            }

        return Response(
            {
                "trend_data": trend_data,
                "trend_indicators": trend_indicators,
                "period_months": months,
                "category_id": category_id,
            }
        )

    def _calculate_period_analytics(self, queryset):
        """Calculate analytics for a given budget queryset."""
        total_budget = Decimal("0")
        total_spent = Decimal("0")
        over_budget_count = 0
        budget_count = queryset.count()

        for budget in queryset:
            total_budget += budget.amount
            spent = budget.calculate_spent_amount()
            total_spent += spent

            if spent > budget.amount:
                over_budget_count += 1

        total_remaining = total_budget - total_spent

        if total_budget > 0:
            overall_utilization = (total_spent / total_budget) * Decimal("100")
            overall_utilization = overall_utilization.quantize(Decimal("0.01"))
        else:
            overall_utilization = Decimal("0")

        return {
            "total_budget": str(total_budget),
            "total_spent": str(total_spent),
            "total_remaining": str(total_remaining),
            "overall_utilization_percentage": str(overall_utilization),
            "budget_count": budget_count,
            "over_budget_count": over_budget_count,
        }

    def _calculate_previous_period_analytics(self, period_start_str, period_end_str):
        """Calculate analytics for the previous period."""
        period_start = date.fromisoformat(period_start_str)
        period_end = date.fromisoformat(period_end_str)

        # Calculate period length
        period_length = (period_end - period_start).days

        # Calculate previous period dates
        prev_period_end = period_start - timedelta(days=1)
        prev_period_start = prev_period_end - timedelta(days=period_length)

        # Get previous period budgets
        prev_queryset = Budget.objects.filter(
            user=self.request.user,
            is_active=True,
            period_start__lte=prev_period_end,
            period_end__gte=prev_period_start,
        ).select_related("category")

        analytics = self._calculate_period_analytics(prev_queryset)
        analytics.update(
            {
                "period_start": str(prev_period_start),
                "period_end": str(prev_period_end),
            }
        )

        return analytics

    def _calculate_period_comparison(self, current, previous):
        """Calculate comparison metrics between current and previous periods."""
        current_budget = Decimal(current["total_budget"])
        previous_budget = Decimal(previous["total_budget"])
        current_spent = Decimal(current["total_spent"])
        previous_spent = Decimal(previous["total_spent"])
        current_utilization = Decimal(current["overall_utilization_percentage"])
        previous_utilization = Decimal(previous["overall_utilization_percentage"])

        return {
            "budget_change": self._calculate_percentage_change(
                previous_budget, current_budget
            ),
            "spending_change": self._calculate_percentage_change(
                previous_spent, current_spent
            ),
            "utilization_change": self._calculate_percentage_change(
                previous_utilization, current_utilization
            ),
            "budget_count_change": current["budget_count"] - previous["budget_count"],
        }

    def _calculate_category_breakdown(self, queryset):
        """Calculate category-wise breakdown of budget analytics."""
        category_data = defaultdict(
            lambda: {
                "total_budget": Decimal("0"),
                "total_spent": Decimal("0"),
                "budget_count": 0,
                "over_budget_count": 0,
            }
        )

        for budget in queryset:
            category_name = budget.category.name if budget.category else "Overall"
            spent = budget.calculate_spent_amount()

            category_data[category_name]["total_budget"] += budget.amount
            category_data[category_name]["total_spent"] += spent
            category_data[category_name]["budget_count"] += 1

            if spent > budget.amount:
                category_data[category_name]["over_budget_count"] += 1

        # Convert to serializable format
        breakdown = []
        for category_name, data in category_data.items():
            total_budget = data["total_budget"]
            total_spent = data["total_spent"]

            if total_budget > 0:
                utilization = (total_spent / total_budget) * Decimal("100")
                utilization = utilization.quantize(Decimal("0.01"))
            else:
                utilization = Decimal("0")

            breakdown.append(
                {
                    "category": category_name,
                    "total_budget": str(total_budget),
                    "total_spent": str(total_spent),
                    "total_remaining": str(total_budget - total_spent),
                    "utilization_percentage": str(utilization),
                    "budget_count": data["budget_count"],
                    "over_budget_count": data["over_budget_count"],
                }
            )

        # Sort by total budget descending
        breakdown.sort(key=lambda x: Decimal(x["total_budget"]), reverse=True)
        return breakdown

    def _calculate_percentage_change(self, old_value, new_value):
        """Calculate percentage change between two values."""
        if old_value == 0:
            return "0.00" if new_value == 0 else "100.00"

        change = ((new_value - old_value) / old_value) * Decimal("100")
        return str(change.quantize(Decimal("0.01")))
