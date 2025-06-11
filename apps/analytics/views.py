"""
Analytics views for report generation and data analysis.
"""

from datetime import date, timedelta

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import View

from apps.analytics.models import SpendingAnalytics
from apps.analytics.reports import ExcelReportGenerator, PDFReportGenerator


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
