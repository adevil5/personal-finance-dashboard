"""
Analytics views for report generation and data analysis.
"""

from datetime import date, timedelta
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Sum
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import View

from apps.analytics.models import SpendingAnalytics
from apps.analytics.reports import ExcelReportGenerator, PDFReportGenerator
from apps.expenses.models import Transaction


@method_decorator(login_required, name="dispatch")
class BaseReportView(View):
    """Base view for report generation."""

    def get_date_range(self, request):
        """
        Get date range from request parameters.

        Returns:
            tuple: (start_date, end_date)
        """
        # Default to last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        # Override with request parameters if provided
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
            except ValueError:
                pass  # Keep default

        if end_date_str:
            try:
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                pass  # Keep default

        return start_date, end_date


class ExcelReportView(BaseReportView):
    """Generate Excel spending reports."""

    def get(self, request):
        """Generate and return Excel report."""
        start_date, end_date = self.get_date_range(request)

        try:
            generator = ExcelReportGenerator(request.user, start_date, end_date)
            excel_data = generator.generate_spending_report()

            response = HttpResponse(
                excel_data,
                content_type=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            )
            filename = f"spending_report_{start_date}_to_{end_date}.xlsx"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            return HttpResponse(
                f"Error generating report: {str(e)}",
                status=500,
                content_type="text/plain",
            )


class PDFReportView(BaseReportView):
    """Generate PDF spending reports."""

    def get(self, request):
        """Generate and return PDF report."""
        start_date, end_date = self.get_date_range(request)

        try:
            generator = PDFReportGenerator(request.user, start_date, end_date)
            pdf_data = generator.generate_spending_report()

            response = HttpResponse(pdf_data, content_type="application/pdf")
            filename = f"spending_report_{start_date}_to_{end_date}.pdf"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

            return response

        except Exception as e:
            return HttpResponse(
                f"Error generating report: {str(e)}",
                status=500,
                content_type="text/plain",
            )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_summary(request):
    """
    Get analytics summary data via API.

    Query parameters:
    - start_date: Start date (YYYY-MM-DD format)
    - end_date: End date (YYYY-MM-DD format)
    """
    from apps.analytics.models import SpendingAnalytics

    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid start_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid end_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if start_date > end_date:
        return Response(
            {"error": "Start date must be before or equal to end date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        analytics = SpendingAnalytics(request.user, start_date, end_date)

        data = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": {
                "total_spending": float(analytics.get_total_spending()),
                "transaction_count": analytics.get_transaction_count(),
                "average_daily_spending": float(analytics.get_average_daily_spending()),
                "average_transaction_amount": float(
                    analytics.get_average_transaction_amount()
                ),
            },
            "category_breakdown": {
                category: float(amount)
                for category, amount in analytics.get_category_breakdown().items()
            },
            "top_categories": [
                {"category": item["category"], "amount": float(item["amount"])}
                for item in analytics.get_top_spending_categories(limit=5)
            ],
            "spending_by_day_of_week": {
                day: float(amount)
                for day, amount in analytics.get_spending_by_day_of_week().items()
            },
        }

        return Response(data)

    except Exception as e:
        return Response(
            {"error": f"Error generating analytics: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def spending_trends(request):
    """
    Get spending trends over time.

    Query parameters:
    - period: Trend period (daily, weekly, monthly) - default: daily
    - start_date: Start date (YYYY-MM-DD format)
    - end_date: End date (YYYY-MM-DD format)
    """
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid start_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid end_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if start_date > end_date:
        return Response(
            {"error": "Start date must be before or equal to end date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get period parameter
    period = request.GET.get("period", "daily")
    if period not in ["daily", "weekly", "monthly"]:
        return Response(
            {"error": "Period must be 'daily', 'weekly', or 'monthly'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        analytics = SpendingAnalytics(request.user, start_date, end_date)
        trends = analytics.get_spending_trends(period)

        # Convert Decimal amounts to float for JSON serialization
        trends_data = [
            {
                "date": trend["date"].isoformat(),
                "amount": float(trend["amount"]),
            }
            for trend in trends
        ]

        data = {
            "trends": trends_data,
            "period": period,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "total_data_points": len(trends_data),
        }

        return Response(data)

    except Exception as e:
        return Response(
            {"error": f"Error generating spending trends: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def category_breakdown(request):
    """
    Get detailed category breakdown with percentages.

    Query parameters:
    - start_date: Start date (YYYY-MM-DD format)
    - end_date: End date (YYYY-MM-DD format)
    """
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid start_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid end_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if start_date > end_date:
        return Response(
            {"error": "Start date must be before or equal to end date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        analytics = SpendingAnalytics(request.user, start_date, end_date)
        breakdown = analytics.get_category_breakdown()
        total_spending = analytics.get_total_spending()

        # Convert to list with percentages
        categories_data = []
        for category_name, amount in breakdown.items():
            percentage = (
                (float(amount) / float(total_spending) * 100)
                if total_spending > 0
                else 0
            )
            categories_data.append(
                {
                    "name": category_name,
                    "amount": float(amount),
                    "percentage": round(percentage, 1),
                }
            )

        # Sort by amount descending
        categories_data.sort(key=lambda x: x["amount"], reverse=True)

        data = {
            "categories": categories_data,
            "total_spending": float(total_spending),
            "category_count": len(categories_data),
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        return Response(data)

    except Exception as e:
        return Response(
            {"error": f"Error generating category breakdown: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def spending_comparison(request):
    """
    Compare spending between two periods.

    Query parameters:
    - current_start: Current period start date (YYYY-MM-DD format)
    - current_end: Current period end date (YYYY-MM-DD format)
    - comparison_start: Comparison period start date (YYYY-MM-DD format)
    - comparison_end: Comparison period end date (YYYY-MM-DD format)
    """
    # Get required parameters
    current_start_str = request.GET.get("current_start")
    current_end_str = request.GET.get("current_end")
    comparison_start_str = request.GET.get("comparison_start")
    comparison_end_str = request.GET.get("comparison_end")

    if not all(
        [current_start_str, current_end_str, comparison_start_str, comparison_end_str]
    ):
        return Response(
            {
                "error": "All date parameters are required: "
                "current_start, current_end, comparison_start, comparison_end"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        current_start = date.fromisoformat(current_start_str)
        current_end = date.fromisoformat(current_end_str)
        comparison_start = date.fromisoformat(comparison_start_str)
        comparison_end = date.fromisoformat(comparison_end_str)
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if current_start > current_end or comparison_start > comparison_end:
        return Response(
            {
                "error": "Start date must be before or equal to end date "
                "for both periods."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        analytics = SpendingAnalytics(request.user, current_start, current_end)
        comparison_data = analytics.get_spending_comparison(
            comparison_start, comparison_end
        )

        data = {
            "current_period": float(comparison_data["current_period"]),
            "comparison_period": float(comparison_data["comparison_period"]),
            "change_amount": float(comparison_data["change_amount"]),
            "change_percentage": float(comparison_data["change_percentage"]),
            "periods": {
                "current": {
                    "start_date": current_start.isoformat(),
                    "end_date": current_end.isoformat(),
                },
                "comparison": {
                    "start_date": comparison_start.isoformat(),
                    "end_date": comparison_end.isoformat(),
                },
            },
        }

        return Response(data)

    except Exception as e:
        return Response(
            {"error": f"Error generating spending comparison: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def top_categories(request):
    """
    Get top spending categories.

    Query parameters:
    - limit: Number of categories to return (default: 5, max: 20)
    - start_date: Start date (YYYY-MM-DD format)
    - end_date: End date (YYYY-MM-DD format)
    """
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid start_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid end_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if start_date > end_date:
        return Response(
            {"error": "Start date must be before or equal to end date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get limit parameter
    limit_str = request.GET.get("limit", "5")
    try:
        limit = int(limit_str)
        if limit < 1 or limit > 20:
            limit = 5
    except ValueError:
        limit = 5

    try:
        analytics = SpendingAnalytics(request.user, start_date, end_date)
        top_categories_data = analytics.get_top_spending_categories(limit=limit)

        # Convert Decimal amounts to float
        categories_data = [
            {
                "category": item["category"],
                "amount": float(item["amount"]),
            }
            for item in top_categories_data
        ]

        data = {
            "categories": categories_data,
            "limit": limit,
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        return Response(data)

    except Exception as e:
        return Response(
            {"error": f"Error generating top categories: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def day_of_week_analysis(request):
    """
    Get spending analysis by day of the week.

    Query parameters:
    - start_date: Start date (YYYY-MM-DD format)
    - end_date: End date (YYYY-MM-DD format)
    """
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")

    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid start_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if end_date_str:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                {"error": "Invalid end_date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if start_date > end_date:
        return Response(
            {"error": "Start date must be before or equal to end date."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        analytics = SpendingAnalytics(request.user, start_date, end_date)
        spending_by_day = analytics.get_spending_by_day_of_week()
        total_spending = analytics.get_total_spending()

        # Convert Decimal amounts to float
        spending_data = {day: float(amount) for day, amount in spending_by_day.items()}

        data = {
            "spending_by_day": spending_data,
            "total_spending": float(total_spending),
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

        return Response(data)

    except Exception as e:
        return Response(
            {"error": f"Error generating day of week analysis: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_metrics(request):
    """
    Get comprehensive dashboard metrics for current or specified month.

    Query parameters:
    - year: Year for metrics (default: current year)
    - month: Month for metrics (default: current month)
    """
    # Parse year and month parameters
    current_date = date.today()
    year = current_date.year
    month = current_date.month

    year_param = request.GET.get("year")
    month_param = request.GET.get("month")

    if year_param:
        try:
            year = int(year_param)
            if year < 1900 or year > current_date.year:
                return Response(
                    {"error": "Year must be between 1900 and current year."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ValueError:
            return Response(
                {"error": "Invalid year format. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if month_param:
        try:
            month = int(month_param)
            if month < 1 or month > 12:
                return Response(
                    {"error": "Month must be between 1 and 12."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ValueError:
            return Response(
                {"error": "Invalid month format. Must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Check if requesting future date
    request_date = date(year, month, 1)
    if request_date > current_date.replace(day=1):
        return Response(
            {"error": "Cannot request metrics for future months."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Generate cache key
    cache_key = f"dashboard_metrics_{request.user.id}_{year}_{month}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)

    try:
        # Calculate month boundaries
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        # Get current month analytics
        analytics = SpendingAnalytics(request.user, month_start, month_end)

        # Calculate basic metrics
        total_income = _get_total_income(request.user, month_start, month_end)
        total_expenses = analytics.get_total_spending()
        net_savings = total_income - total_expenses
        savings_rate = (
            float((net_savings / total_income) * 100) if total_income > 0 else 0.0
        )

        # Get previous month for comparison
        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year

        prev_month_start = date(prev_year, prev_month, 1)
        if prev_month == 12:
            prev_month_end = date(prev_year + 1, 1, 1) - timedelta(days=1)
        else:
            prev_month_end = date(prev_year, prev_month + 1, 1) - timedelta(days=1)

        # Calculate previous month metrics
        prev_analytics = SpendingAnalytics(
            request.user, prev_month_start, prev_month_end
        )
        prev_total_income = _get_total_income(
            request.user, prev_month_start, prev_month_end
        )
        prev_total_expenses = prev_analytics.get_total_spending()
        prev_net_savings = prev_total_income - prev_total_expenses

        # Month-over-month comparisons
        income_change = total_income - prev_total_income
        expense_change = total_expenses - prev_total_expenses
        savings_change = net_savings - prev_net_savings

        income_change_pct = (
            float((income_change / prev_total_income) * 100)
            if prev_total_income > 0
            else 0.0
        )
        expense_change_pct = (
            float((expense_change / prev_total_expenses) * 100)
            if prev_total_expenses > 0
            else 0.0
        )
        savings_change_pct = (
            float((savings_change / prev_net_savings) * 100)
            if prev_net_savings > 0
            else 0.0
        )

        # Get top spending categories for current month
        category_breakdown = analytics.get_category_breakdown()
        top_categories = []
        for category_name, amount in sorted(
            category_breakdown.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            percentage = (
                float((amount / total_expenses) * 100) if total_expenses > 0 else 0.0
            )
            top_categories.append(
                {
                    "name": category_name,
                    "amount": float(amount),
                    "percentage": round(percentage, 1),
                }
            )

        # Get recent transactions (last 5)
        recent_transactions = (
            Transaction.objects.filter(user=request.user, is_active=True)
            .select_related("category")
            .order_by("-date", "-created_at")[:5]
        )

        recent_trans_data = []
        for trans in recent_transactions:
            recent_trans_data.append(
                {
                    "id": trans.id,
                    "amount": float(trans.amount_index),
                    "category": (
                        trans.category.name if trans.category else "Uncategorized"
                    ),
                    "date": trans.date.isoformat(),
                    "transaction_type": trans.transaction_type,
                    "merchant": trans.merchant if trans.merchant else "",
                }
            )

        # Calculate daily spending average
        days_in_period = (month_end - month_start).days + 1
        if (
            request_date.month == current_date.month
            and request_date.year == current_date.year
        ):
            # Current month - use days passed so far
            days_passed = (current_date - month_start).days + 1
            avg_daily = float(total_expenses / days_passed) if days_passed > 0 else 0.0
        else:
            # Historical month - use all days
            avg_daily = (
                float(total_expenses / days_in_period) if days_in_period > 0 else 0.0
            )

        # Get budget summary
        budget_summary = _get_budget_summary(request.user, month_start, month_end)

        # Build response data
        data = {
            "period": {
                "year": year,
                "month": month,
                "start_date": month_start.isoformat(),
                "end_date": month_end.isoformat(),
            },
            "current_month": {
                "total_income": float(total_income),
                "total_expenses": float(total_expenses),
                "net_savings": float(net_savings),
                "savings_rate": round(savings_rate, 1),
            },
            "month_over_month": {
                "income_change": {
                    "amount": float(income_change),
                    "percentage": round(income_change_pct, 2),
                },
                "expense_change": {
                    "amount": float(expense_change),
                    "percentage": round(expense_change_pct, 2),
                },
                "savings_change": {
                    "amount": float(savings_change),
                    "percentage": round(savings_change_pct, 2),
                },
            },
            "metrics": {
                "transaction_count": analytics.get_transaction_count()
                + _get_income_transaction_count(request.user, month_start, month_end),
                "average_daily_spending": round(avg_daily, 2),
                "average_transaction_amount": float(
                    analytics.get_average_transaction_amount()
                ),
            },
            "top_categories": top_categories,
            "recent_transactions": recent_trans_data,
            "budget_summary": budget_summary,
        }

        # Cache for 1 hour (3600 seconds)
        cache.set(cache_key, data, 3600)

        return Response(data)

    except Exception as e:
        return Response(
            {"error": f"Error generating dashboard metrics: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _get_total_income(user, start_date, end_date):
    """Get total income for user in date range."""
    result = Transaction.objects.filter(
        user=user,
        transaction_type=Transaction.INCOME,
        date__gte=start_date,
        date__lte=end_date,
        is_active=True,
    ).aggregate(total=Sum("amount_index"))
    return result["total"] or Decimal("0.00")


def _get_income_transaction_count(user, start_date, end_date):
    """Get count of income transactions for user in date range."""
    return Transaction.objects.filter(
        user=user,
        transaction_type=Transaction.INCOME,
        date__gte=start_date,
        date__lte=end_date,
        is_active=True,
    ).count()


def _get_budget_summary(user, start_date, end_date):
    """Get budget summary for the period."""
    try:
        from apps.budgets.models import Budget

        # Get active budgets that overlap with the period
        budgets = Budget.objects.filter(
            user=user,
            is_active=True,
            period_start__lte=end_date,
            period_end__gte=start_date,
        )

        if not budgets.exists():
            return {
                "total_budgets": 0,
                "over_budget_count": 0,
                "total_budget_amount": 0.0,
                "total_budget_spent": 0.0,
                "overall_utilization": 0.0,
            }

        total_budget_amount = Decimal("0.00")
        total_budget_spent = Decimal("0.00")
        over_budget_count = 0

        for budget in budgets:
            total_budget_amount += budget.amount
            spent_amount = budget.calculate_spent_amount()  # This uses the method
            total_budget_spent += spent_amount

            if spent_amount > budget.amount:
                over_budget_count += 1

        overall_utilization = (
            float((total_budget_spent / total_budget_amount) * 100)
            if total_budget_amount > 0
            else 0.0
        )

        return {
            "total_budgets": budgets.count(),
            "over_budget_count": over_budget_count,
            "total_budget_amount": float(total_budget_amount),
            "total_budget_spent": float(total_budget_spent),
            "overall_utilization": round(overall_utilization, 2),
        }

    except ImportError:
        # Budget app not available
        return {
            "total_budgets": 0,
            "over_budget_count": 0,
            "total_budget_amount": 0.0,
            "total_budget_spent": 0.0,
            "overall_utilization": 0.0,
        }
