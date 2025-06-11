from django.urls import path

from apps.analytics.views import ExcelReportView, PDFReportView, analytics_summary

app_name = "analytics"

urlpatterns = [
    # Report generation endpoints
    path("reports/excel/", ExcelReportView.as_view(), name="excel_report"),
    path("reports/pdf/", PDFReportView.as_view(), name="pdf_report"),
    # API endpoints
    path("api/summary/", analytics_summary, name="analytics_summary"),
]
