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
