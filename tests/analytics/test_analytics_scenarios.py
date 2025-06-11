"""
Tests for analytics engine with various data scenarios.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.models import SpendingAnalytics
from tests.factories import CategoryFactory, TransactionFactory, UserFactory

User = get_user_model()


class SpendingAnalyticsScenarioTestCase(TestCase):
    """Test case for spending analytics with various data scenarios."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()

        # Create categories
        self.food_category = CategoryFactory(user=self.user, name="Food")
        self.transport_category = CategoryFactory(user=self.user, name="Transport")

        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=30)

    def test_scenario_large_amounts(self):
        """Test analytics with very large transaction amounts."""
        # Create large transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            amount=Decimal("99999.99"),
            date=self.start_date,
            transaction_type="expense",
        )
        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            amount=Decimal("50000.50"),
            date=self.start_date + timedelta(days=1),
            transaction_type="expense",
        )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        total = analytics.get_total_spending()
        self.assertEqual(total, Decimal("150000.49"))

        breakdown = analytics.get_category_breakdown()
        self.assertEqual(breakdown["Food"], Decimal("99999.99"))
        self.assertEqual(breakdown["Transport"], Decimal("50000.50"))

    def test_scenario_small_amounts(self):
        """Test analytics with very small transaction amounts."""
        # Create small transactions
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            amount=Decimal("0.01"),
            date=self.start_date,
            transaction_type="expense",
        )
        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            amount=Decimal("0.99"),
            date=self.start_date + timedelta(days=1),
            transaction_type="expense",
        )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        total = analytics.get_total_spending()
        self.assertEqual(total, Decimal("1.00"))

        avg_transaction = analytics.get_average_transaction_amount()
        self.assertEqual(avg_transaction, Decimal("0.50"))

    def test_scenario_many_transactions(self):
        """Test analytics with many transactions (stress test)."""
        # Create 100 transactions across the date range
        for i in range(100):
            days_offset = i % 30  # Distribute across 30 days
            TransactionFactory(
                user=self.user,
                category=self.food_category,
                amount=Decimal("10.00"),
                date=self.start_date + timedelta(days=days_offset),
                transaction_type="expense",
            )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        total = analytics.get_total_spending()
        self.assertEqual(total, Decimal("1000.00"))  # 100 * 10.00

        transaction_count = analytics.get_transaction_count()
        self.assertEqual(transaction_count, 100)

        avg_transaction = analytics.get_average_transaction_amount()
        self.assertEqual(avg_transaction, Decimal("10.00"))

    def test_scenario_single_category_dominance(self):
        """Test analytics where one category dominates spending."""
        # Create transactions where food is 95% of spending
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            amount=Decimal("950.00"),
            date=self.start_date,
            transaction_type="expense",
        )
        TransactionFactory(
            user=self.user,
            category=self.transport_category,
            amount=Decimal("50.00"),
            date=self.start_date + timedelta(days=1),
            transaction_type="expense",
        )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        top_categories = analytics.get_top_spending_categories(limit=2)

        self.assertEqual(len(top_categories), 2)
        self.assertEqual(top_categories[0]["category"], "Food")
        self.assertEqual(top_categories[0]["amount"], Decimal("950.00"))
        self.assertEqual(top_categories[1]["category"], "Transport")
        self.assertEqual(top_categories[1]["amount"], Decimal("50.00"))

    def test_scenario_equal_spending_categories(self):
        """Test analytics with equal spending across categories."""
        # Create equal spending across categories
        categories = [self.food_category, self.transport_category]
        for i, category in enumerate(categories):
            TransactionFactory(
                user=self.user,
                category=category,
                amount=Decimal("100.00"),
                date=self.start_date + timedelta(days=i),
                transaction_type="expense",
            )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        breakdown = analytics.get_category_breakdown()

        # Both categories should have equal amounts
        self.assertEqual(breakdown["Food"], Decimal("100.00"))
        self.assertEqual(breakdown["Transport"], Decimal("100.00"))

        total = analytics.get_total_spending()
        self.assertEqual(total, Decimal("200.00"))

    def test_scenario_spending_concentrated_in_few_days(self):
        """Test analytics where spending is concentrated in just a few days."""
        # All spending on just 3 days out of 30
        spending_days = [0, 10, 20]  # Days 1, 11, 21
        for day_offset in spending_days:
            TransactionFactory(
                user=self.user,
                category=self.food_category,
                amount=Decimal("333.33"),
                date=self.start_date + timedelta(days=day_offset),
                transaction_type="expense",
            )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        daily_trends = analytics.get_spending_trends(period="daily")

        # Should have 30 days of data
        self.assertEqual(len(daily_trends), 31)  # 31 days in range

        # Count days with spending
        spending_days_count = sum(
            1 for trend in daily_trends if trend["amount"] > Decimal("0")
        )
        self.assertEqual(spending_days_count, 3)

        # Count days without spending
        zero_spending_days = sum(
            1 for trend in daily_trends if trend["amount"] == Decimal("0")
        )
        self.assertEqual(zero_spending_days, 28)

    def test_scenario_gradual_spending_increase(self):
        """Test analytics with gradually increasing spending over time."""
        # Create transactions with increasing amounts
        for i in range(10):
            amount = Decimal(str(10 + i * 5))  # 10, 15, 20, 25, etc.
            TransactionFactory(
                user=self.user,
                category=self.food_category,
                amount=amount,
                date=self.start_date + timedelta(days=i * 2),
                transaction_type="expense",
            )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        total = analytics.get_total_spending()
        # Sum of arithmetic sequence: 10+15+20+...+55 = 325
        expected_total = sum(Decimal(str(10 + i * 5)) for i in range(10))
        self.assertEqual(total, expected_total)

    def test_scenario_weekend_vs_weekday_spending(self):
        """Test analytics with different spending patterns on weekends vs weekdays."""
        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        # Create transactions for different days of the week
        current_date = self.start_date
        while current_date <= self.end_date:
            # Higher spending on weekends (Saturday=5, Sunday=6)
            if current_date.weekday() in [5, 6]:  # Weekend
                amount = Decimal("100.00")
            else:  # Weekday
                amount = Decimal("50.00")

            TransactionFactory(
                user=self.user,
                category=self.food_category,
                amount=amount,
                date=current_date,
                transaction_type="expense",
            )
            current_date += timedelta(days=1)

        spending_by_dow = analytics.get_spending_by_day_of_week()

        # Weekend days should have higher spending
        weekend_days = ["Saturday", "Sunday"]
        weekday_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

        # Check that weekend spending is generally higher
        weekend_total = sum(
            spending_by_dow.get(day, Decimal("0")) for day in weekend_days
        )
        weekday_total = sum(
            spending_by_dow.get(day, Decimal("0")) for day in weekday_days
        )

        # Since we have more weekdays than weekend days,
        # check average spending per day type
        weekend_avg = weekend_total / 2  # 2 weekend days
        weekday_avg = weekday_total / 5  # 5 weekdays

        self.assertGreater(weekend_avg, weekday_avg)

    def test_scenario_mixed_transaction_types(self):
        """Test analytics properly filters out non-expense transactions."""
        # Create mix of transaction types
        TransactionFactory(
            user=self.user,
            category=self.food_category,
            amount=Decimal("100.00"),
            date=self.start_date,
            transaction_type="expense",
        )
        TransactionFactory(
            user=self.user,
            amount=Decimal("1000.00"),
            date=self.start_date + timedelta(days=1),
            transaction_type="income",
            category=None,
        )
        TransactionFactory(
            user=self.user,
            amount=Decimal("200.00"),
            date=self.start_date + timedelta(days=2),
            transaction_type="transfer",
            category=None,
        )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        # Should only include expense transactions
        total = analytics.get_total_spending()
        self.assertEqual(total, Decimal("100.00"))

        transaction_count = analytics.get_transaction_count()
        self.assertEqual(transaction_count, 1)

    def test_scenario_cross_month_spending(self):
        """Test analytics with spending across multiple months."""
        # Create date range spanning 3 months
        start_date = date(2024, 1, 15)
        end_date = date(2024, 3, 15)

        # Create transactions in each month
        months = [date(2024, 1, 20), date(2024, 2, 10), date(2024, 3, 5)]

        for month_date in months:
            TransactionFactory(
                user=self.user,
                category=self.food_category,
                amount=Decimal("300.00"),
                date=month_date,
                transaction_type="expense",
            )

        analytics = SpendingAnalytics(
            user=self.user, start_date=start_date, end_date=end_date
        )

        monthly_trends = analytics.get_spending_trends(period="monthly")

        # Should have 3 months of data
        self.assertEqual(len(monthly_trends), 3)

        # Each month should have $300 spending
        for trend in monthly_trends:
            self.assertEqual(trend["amount"], Decimal("300.00"))

    def test_scenario_decimal_precision(self):
        """Test analytics with precise decimal calculations."""
        # Create transactions with precise decimal amounts
        amounts = [Decimal("33.33"), Decimal("33.34"), Decimal("33.33")]

        for i, amount in enumerate(amounts):
            TransactionFactory(
                user=self.user,
                category=self.food_category,
                amount=amount,
                date=self.start_date + timedelta(days=i),
                transaction_type="expense",
            )

        analytics = SpendingAnalytics(
            user=self.user, start_date=self.start_date, end_date=self.end_date
        )

        total = analytics.get_total_spending()
        self.assertEqual(total, Decimal("100.00"))

        avg_transaction = analytics.get_average_transaction_amount()
        expected_avg = Decimal("100.00") / 3
        self.assertEqual(
            avg_transaction.quantize(Decimal("0.01")),
            expected_avg.quantize(Decimal("0.01")),
        )
