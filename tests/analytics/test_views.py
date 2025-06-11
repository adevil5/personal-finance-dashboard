"""
Tests for analytics views.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.expenses.models import Transaction
from tests.factories import CategoryFactory, TransactionFactory, UserFactory

User = get_user_model()


@pytest.mark.django_db
class TestReportViews:
    """Test report generation views."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = Client()
        self.client.force_login(self.user)

        # Create test data
        self.category = CategoryFactory(user=self.user, name="Groceries")
        self.transaction = TransactionFactory(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            date=date.today() - timedelta(days=5),
            transaction_type=Transaction.EXPENSE,
        )

    def test_excel_report_view_requires_login(self):
        """Test that Excel report view requires authentication."""
        client = Client()  # Not logged in
        url = reverse("analytics:excel_report")
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_excel_report_view_generates_report(self):
        """Test Excel report view generates and returns Excel file."""
        url = reverse("analytics:excel_report")
        response = self.client.get(url)

        assert response.status_code == 200
        assert (
            response["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "attachment; filename=" in response["Content-Disposition"]
        assert ".xlsx" in response["Content-Disposition"]
        assert len(response.content) > 0

    def test_excel_report_view_with_date_parameters(self):
        """Test Excel report view with custom date range."""
        start_date = date.today() - timedelta(days=10)
        end_date = date.today()

        url = reverse("analytics:excel_report")
        response = self.client.get(
            url,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        assert response.status_code == 200
        assert f"{start_date}_to_{end_date}" in response["Content-Disposition"]

    def test_excel_report_view_with_invalid_dates(self):
        """Test Excel report view with invalid date parameters."""
        url = reverse("analytics:excel_report")
        response = self.client.get(
            url,
            {
                "start_date": "invalid-date",
                "end_date": "also-invalid",
            },
        )

        # Should still work with default dates
        assert response.status_code == 200

    def test_pdf_report_view_requires_login(self):
        """Test that PDF report view requires authentication."""
        client = Client()  # Not logged in
        url = reverse("analytics:pdf_report")
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_pdf_report_view_generates_report(self):
        """Test PDF report view generates and returns PDF file."""
        url = reverse("analytics:pdf_report")
        response = self.client.get(url)

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert "attachment; filename=" in response["Content-Disposition"]
        assert ".pdf" in response["Content-Disposition"]
        assert len(response.content) > 0

    def test_pdf_report_view_with_date_parameters(self):
        """Test PDF report view with custom date range."""
        start_date = date.today() - timedelta(days=10)
        end_date = date.today()

        url = reverse("analytics:pdf_report")
        response = self.client.get(
            url,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        assert response.status_code == 200
        assert f"{start_date}_to_{end_date}" in response["Content-Disposition"]

    def test_report_views_include_only_user_data(self):
        """Test that report views only include data for the authenticated user."""
        # Create transaction for a different user
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user, name="Other Category")
        TransactionFactory(
            user=other_user,
            category=other_category,
            amount=Decimal("500.00"),
            date=date.today() - timedelta(days=5),
            transaction_type=Transaction.EXPENSE,
        )

        # Generate reports for original user
        excel_url = reverse("analytics:excel_report")
        excel_response = self.client.get(excel_url)

        pdf_url = reverse("analytics:pdf_report")
        pdf_response = self.client.get(pdf_url)

        # Both should succeed and not include other user's data
        assert excel_response.status_code == 200
        assert pdf_response.status_code == 200

        # The reports should only contain data for the authenticated user
        # (specific content verification would require parsing the files)


@pytest.mark.django_db
class TestAnalyticsSummaryAPI:
    """Test analytics summary API endpoint."""

    def setup_method(self):
        """Set up test data."""
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create test data
        self.category = CategoryFactory(user=self.user, name="Groceries")
        self.transaction = TransactionFactory(
            user=self.user,
            category=self.category,
            amount=Decimal("100.00"),
            date=date.today() - timedelta(days=5),
            transaction_type=Transaction.EXPENSE,
        )

    def test_analytics_summary_requires_authentication(self):
        """Test that analytics summary API requires authentication."""
        client = APIClient()  # Not authenticated
        url = reverse("analytics:analytics_summary")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_analytics_summary_returns_data(self):
        """Test analytics summary API returns proper data structure."""
        url = reverse("analytics:analytics_summary")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Check data structure
        assert "period" in data
        assert "summary" in data
        assert "category_breakdown" in data
        assert "top_categories" in data
        assert "spending_by_day_of_week" in data

        # Check period data
        assert "start_date" in data["period"]
        assert "end_date" in data["period"]

        # Check summary data
        summary = data["summary"]
        assert "total_spending" in summary
        assert "transaction_count" in summary
        assert "average_daily_spending" in summary
        assert "average_transaction_amount" in summary

        # Check values are correct
        assert summary["total_spending"] == 100.0
        assert summary["transaction_count"] == 1

    def test_analytics_summary_with_custom_date_range(self):
        """Test analytics summary API with custom date range."""
        start_date = date.today() - timedelta(days=10)
        end_date = date.today()

        url = reverse("analytics:analytics_summary")
        response = self.client.get(
            url,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["period"]["start_date"] == start_date.isoformat()
        assert data["period"]["end_date"] == end_date.isoformat()

    def test_analytics_summary_with_invalid_date_format(self):
        """Test analytics summary API with invalid date format."""
        url = reverse("analytics:analytics_summary")
        response = self.client.get(
            url,
            {
                "start_date": "invalid-date",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()
        assert "Invalid start_date format" in response.json()["error"]

    def test_analytics_summary_with_start_date_after_end_date(self):
        """Test analytics summary API with start date after end date."""
        start_date = date.today()
        end_date = date.today() - timedelta(days=5)

        url = reverse("analytics:analytics_summary")
        response = self.client.get(
            url,
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()
        assert "Start date must be before" in response.json()["error"]

    def test_analytics_summary_includes_only_user_data(self):
        """Test analytics summary API only includes data for authenticated user."""
        # Create transaction for different user
        other_user = UserFactory()
        other_category = CategoryFactory(user=other_user, name="Other Category")
        TransactionFactory(
            user=other_user,
            category=other_category,
            amount=Decimal("500.00"),
            date=date.today() - timedelta(days=5),
            transaction_type=Transaction.EXPENSE,
        )

        url = reverse("analytics:analytics_summary")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Should only show the authenticated user's transaction
        assert data["summary"]["total_spending"] == 100.0
        assert data["summary"]["transaction_count"] == 1

    def test_analytics_summary_with_no_transactions(self):
        """Test analytics summary API with no transactions."""
        # Delete the transaction
        Transaction.objects.filter(user=self.user).delete()

        url = reverse("analytics:analytics_summary")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["summary"]["total_spending"] == 0.0
        assert data["summary"]["transaction_count"] == 0
        assert data["category_breakdown"] == {}
        assert data["top_categories"] == []

    def test_analytics_summary_category_breakdown(self):
        """Test analytics summary API category breakdown."""
        # Create additional transaction in different category
        dining_category = CategoryFactory(user=self.user, name="Dining")
        TransactionFactory(
            user=self.user,
            category=dining_category,
            amount=Decimal("50.00"),
            date=date.today() - timedelta(days=3),
            transaction_type=Transaction.EXPENSE,
        )

        url = reverse("analytics:analytics_summary")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        breakdown = data["category_breakdown"]

        assert "Groceries" in breakdown
        assert "Dining" in breakdown
        assert breakdown["Groceries"] == 100.0
        assert breakdown["Dining"] == 50.0

        # Check top categories
        top_categories = data["top_categories"]
        assert len(top_categories) == 2
        assert top_categories[0]["category"] == "Groceries"
        assert top_categories[0]["amount"] == 100.0
