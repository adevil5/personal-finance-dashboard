from django.urls import path

from apps.analytics.views import (
    ExcelReportView,
    PDFReportView,
    analytics_summary,
    category_breakdown,
    day_of_week_analysis,
    spending_comparison,
    spending_trends,
    top_categories,
)

app_name = "analytics"

urlpatterns = [
    # Report generation endpoints
    path("reports/excel/", ExcelReportView.as_view(), name="excel_report"),
    path("reports/pdf/", PDFReportView.as_view(), name="pdf_report"),
    # API endpoints
    path("api/summary/", analytics_summary, name="analytics_summary"),
    path("api/trends/", spending_trends, name="api_spending_trends"),
    path("api/categories/", category_breakdown, name="api_category_breakdown"),
    path("api/comparison/", spending_comparison, name="api_spending_comparison"),
    path("api/top-categories/", top_categories, name="api_top_categories"),
    path("api/day-of-week/", day_of_week_analysis, name="api_day_of_week"),
]
