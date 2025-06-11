"""
Tests for analytics engine functionality.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import SpendingAnalytics
from tests.factories import CategoryFactory, TransactionFactory, UserFactory

User = get_user_model()


class SpendingAnalyticsTestCase(TestCase):
    """Test case for spending analytics functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.other_user = UserFactory()

        # Create categories
        self.food_category = CategoryFactory(user=self.user, name="Food")
        self.transport_category = CategoryFactory(user=self.user, name="Transport")
        self.entertainment_category = CategoryFactory(
            user=self.user, name="Entertainment"
        )

        # Create test date range (last 30 days)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=29)

        # Create transactions for the test period
        self.create_test_transactions()

    def create_test_transactions(self):
        """Create test transactions for analytics testing."""
        # Food transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            amount=Decimal("50.00"),
            date=self.start_date,
            transaction_type="expense",
        )
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            amount=Decimal("75.25"),
            date=self.start_date + timedelta(days=7),
            transaction_type="expense",
        )
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            amount=Decimal("40.50"),
            date=self.start_date + timedelta(days=14),
            transaction_type="expense",
        )

        # Transport transactions
        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            amount=Decimal("100.00"),
            date=self.start_date + timedelta(days=3),
            transaction_type="expense",
        )
        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            amount=Decimal("25.75"),
            date=self.start_date + timedelta(days=10),
            transaction_type="expense",
        )

        # Entertainment transactions
        TransactionFactory(
            user=self.user,
            category=self.entertainment_category,
            amount=Decimal("80.00"),
            date=self.start_date + timedelta(days=5),
            transaction_type="expense",
        )

        # Income transaction (should not be included in spending analytics)
        TransactionFactory(
            user=self.user,
            amount=Decimal("2000.00"),
            date=self.start_date + timedelta(days=1),
            transaction_type="income",
            category=None,
        )

        # Transaction from other user (should not be included)
        other_user_category = CategoryFactory(user=self.other_user, name="Food")
        TransactionFactory(
            user=self.other_user,
            category=other_user_category,
            amount=Decimal("999.99"),
            date=self.start_date + timedelta(days=2),
            transaction_type="expense",
        )

    def test_spending_analytics_init(self):
        """Test SpendingAnalytics initialization."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        self.assertEqual(analytics.user, self.user)
        self.assertEqual(analytics.start_date, self.start_date)
        self.assertEqual(analytics.end_date, self.end_date)

    def test_get_total_spending(self):
        """Test total spending calculation."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        # Expected total: 50.00 + 75.25 + 40.50 + 100.00 + 25.75 + 80.00 = 371.50
        expected_total = Decimal("371.50")
        actual_total = analytics.get_total_spending()

        self.assertEqual(actual_total, expected_total)

    def test_get_average_daily_spending(self):
        """Test average daily spending calculation."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        total_spending = Decimal("371.50")
        days_in_period = 30
        expected_avg = total_spending / days_in_period

        actual_avg = analytics.get_average_daily_spending()

        self.assertEqual(
            actual_avg.quantize(Decimal("0.01")), expected_avg.quantize(Decimal("0.01"))
        )

    def test_get_category_breakdown(self):
        """Test category-wise spending breakdown."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        breakdown = analytics.get_category_breakdown()

        # Expected breakdown
        expected_breakdown = {
            "Food": Decimal("165.75"),  # 50.00 + 75.25 + 40.50
            "Transport": Decimal("125.75"),  # 100.00 + 25.75
            "Entertainment": Decimal("80.00"),  # 80.00
        }

        self.assertEqual(len(breakdown), 3)
        for category_name, expected_amount in expected_breakdown.items():
            self.assertIn(category_name, breakdown)
            self.assertEqual(breakdown[category_name], expected_amount)

    def test_get_spending_trends_daily(self):
        """Test daily spending trends."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        trends = analytics.get_spending_trends(period="daily")

        # Should have 30 days of data
        self.assertEqual(len(trends), 30)

        # Check specific dates with transactions
        first_day_spending = trends[0]["amount"]  # start_date
        self.assertEqual(first_day_spending, Decimal("50.00"))

        # Check that days without transactions have zero spending
        zero_days = [trend for trend in trends if trend["amount"] == Decimal("0.00")]
        self.assertTrue(len(zero_days) > 0)

    def test_get_spending_trends_weekly(self):
        """Test weekly spending trends."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        trends = analytics.get_spending_trends(period="weekly")

        # Should have at least 1 week of data for our 30-day period
        self.assertTrue(len(trends) >= 1)
        self.assertTrue(len(trends) <= 6)  # Max 6 weeks for 30-day period

    def test_get_spending_trends_monthly(self):
        """Test monthly spending trends."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        trends = analytics.get_spending_trends(period="monthly")

        # Should have at least 1 month of data for our 30-day period
        self.assertTrue(len(trends) >= 1)
        self.assertTrue(len(trends) <= 2)  # Max 2 months for 30-day period

    def test_get_spending_comparison(self):
        """Test spending comparison between periods."""
        # Create comparison period (previous 30 days)
        comparison_start = self.start_date - timedelta(days=30)
        comparison_end = self.start_date - timedelta(days=1)

        # Create some transactions in the comparison period
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            amount=Decimal("200.00"),
            date=comparison_start + timedelta(days=5),
            transaction_type="expense",
        )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        comparison = analytics.get_spending_comparison(
            comparison_start_date=comparison_start, comparison_end_date=comparison_end
        )

        self.assertIn("current_period", comparison)
        self.assertIn("comparison_period", comparison)
        self.assertIn("change_amount", comparison)
        self.assertIn("change_percentage", comparison)

        # Current period should be 371.50
        self.assertEqual(comparison["current_period"], Decimal("371.50"))
        # Comparison period should be 200.00
        self.assertEqual(comparison["comparison_period"], Decimal("200.00"))
        # Change should be 171.50 increase
        self.assertEqual(comparison["change_amount"], Decimal("171.50"))

    def test_get_top_spending_categories(self):
        """Test getting top spending categories."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        top_categories = analytics.get_top_spending_categories(limit=2)

        self.assertEqual(len(top_categories), 2)

        # Should be sorted by amount descending
        # Food: 165.75, Transport: 125.75, Entertainment: 80.00
        self.assertEqual(top_categories[0]["category"], "Food")
        self.assertEqual(top_categories[0]["amount"], Decimal("165.75"))
        self.assertEqual(top_categories[1]["category"], "Transport")
        self.assertEqual(top_categories[1]["amount"], Decimal("125.75"))

    def test_empty_date_range(self):
        """Test analytics with empty date range."""
        # Create date range with no transactions
        empty_start = date.today() + timedelta(days=100)
        empty_end = date.today() + timedelta(days=130)

        analytics = SpendingAnalytics(
            user=self.user, start_date=empty_start, end_date=empty_end
        )

        self.assertEqual(analytics.get_total_spending(), Decimal("0.00"))
        self.assertEqual(analytics.get_average_daily_spending(), Decimal("0.00"))
        self.assertEqual(len(analytics.get_category_breakdown()), 0)

    def test_single_day_analytics(self):
        """Test analytics for a single day."""
        single_date = self.start_date

        analytics = SpendingAnalytics(
            user=self.user, start_date=single_date, end_date=single_date
        )

        # Should only include transactions from that day (50.00)
        self.assertEqual(analytics.get_total_spending(), Decimal("50.00"))
        self.assertEqual(analytics.get_average_daily_spending(), Decimal("50.00"))

    def test_user_isolation(self):
        """Test that analytics only include the specified user's data."""
        analytics = SpendingAnalytics(
            user=self.other_user, start_date=self.start_date, end_date=self.end_date
        )

        # Other user should have only their own transaction (999.99)
        self.assertEqual(analytics.get_total_spending(), Decimal("999.99"))

    def test_only_expense_transactions(self):
        """Test that only expense transactions are included."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        total = analytics.get_total_spending()

        # Should not include the 2000.00 income transaction
        self.assertEqual(total, Decimal("371.50"))

    def test_invalid_date_range(self):
        """Test handling of invalid date ranges."""
        with self.assertRaises(ValueError):
            SpendingAnalytics(
                user=self.user,
                start_date=self.end_date,  # start after end
                end_date=self.start_date,
            )
