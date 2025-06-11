"""
Analytics models for spending analysis and reporting.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum

from apps.expenses.models import Transaction

User = get_user_model()


class SpendingAnalytics:
    """
    Analytics engine for spending analysis.

    Provides methods to calculate spending trends, category breakdowns,
    averages, and comparisons over specified time periods.
    """

    def __init__(self, user, start_date, end_date):
        """
        Initialize spending analytics for a user and date range.

        Args:
            user: User instance to analyze
            start_date: Start date for analysis period
            end_date: End date for analysis period

        Raises:
            ValueError: If start_date is after end_date
        """
        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")

        self.user = user
        self.start_date = start_date
        self.end_date = end_date

    def get_base_queryset(self):
        """
        Get base queryset for expense transactions in the date range.

        Returns:
            QuerySet: Filtered transactions for the user and date range
        """
        return Transaction.objects.filter(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            date__gte=self.start_date,
            date__lte=self.end_date,
            is_active=True,
        )

    def get_total_spending(self):
        """
        Calculate total spending for the period.

        Returns:
            Decimal: Total amount spent
        """
        result = self.get_base_queryset().aggregate(total=Sum("amount_index"))
        return result["total"] or Decimal("0.00")

    def get_average_daily_spending(self):
        """
        Calculate average daily spending for the period.

        Returns:
            Decimal: Average daily spending amount
        """
        total_spending = self.get_total_spending()
        days_in_period = (self.end_date - self.start_date).days + 1

        if days_in_period == 0:
            return Decimal("0.00")

        return total_spending / days_in_period

    def get_category_breakdown(self):
        """
        Get spending breakdown by category.

        Returns:
            dict: Category name to total amount mapping
        """
        breakdown = {}

        # Get category spending aggregation
        category_spending = (
            self.get_base_queryset()
            .values("category__name")
            .annotate(total_amount=Sum("amount_index"))
            .filter(category__isnull=False)
            .order_by("-total_amount")
        )

        for item in category_spending:
            category_name = item["category__name"]
            total_amount = item["total_amount"] or Decimal("0.00")
            breakdown[category_name] = total_amount

        return breakdown

    def get_spending_trends(self, period="daily"):
        """
        Get spending trends over time.

        Args:
            period: Time period for grouping ("daily", "weekly", "monthly")

        Returns:
            list: List of dicts with date and amount keys
        """
        if period == "daily":
            return self._get_daily_trends()
        elif period == "weekly":
            return self._get_weekly_trends()
        elif period == "monthly":
            return self._get_monthly_trends()
        else:
            raise ValueError("Period must be 'daily', 'weekly', or 'monthly'")

    def _get_daily_trends(self):
        """Get daily spending trends."""
        trends = []
        current_date = self.start_date

        # Get all transactions grouped by date
        daily_spending = {}
        transactions = (
            self.get_base_queryset()
            .values("date")
            .annotate(total_amount=Sum("amount_index"))
        )

        for transaction in transactions:
            daily_spending[transaction["date"]] = transaction[
                "total_amount"
            ] or Decimal("0.00")

        # Create trend data for each day in range
        while current_date <= self.end_date:
            amount = daily_spending.get(current_date, Decimal("0.00"))
            trends.append({"date": current_date, "amount": amount})
            current_date += timedelta(days=1)

        return trends

    def _get_weekly_trends(self):
        """Get weekly spending trends."""
        from django.db import connection
        from django.db.models.functions import Extract

        trends = []

        # SQLite doesn't support DATE_TRUNC, use alternative approach
        if connection.vendor == "sqlite":
            # Group by year and week number for SQLite
            weekly_spending = (
                self.get_base_queryset()
                .annotate(year=Extract("date", "year"), week=Extract("date", "week"))
                .values("year", "week")
                .annotate(total_amount=Sum("amount_index"))
                .order_by("year", "week")
            )

            for item in weekly_spending:
                # Approximate date for the week
                year = item["year"]
                week = item["week"]
                # Use first day of year + (week-1)*7 days as approximation
                from datetime import date

                week_start = date(year, 1, 1) + timedelta(weeks=week - 1)
                trends.append(
                    {
                        "date": week_start,
                        "amount": item["total_amount"] or Decimal("0.00"),
                    }
                )
        else:
            # PostgreSQL version with DATE_TRUNC
            weekly_spending = (
                self.get_base_queryset()
                .extra(
                    select={
                        "week": "DATE_TRUNC('week', date)",
                    }
                )
                .values("week")
                .annotate(total_amount=Sum("amount_index"))
                .order_by("week")
            )

            for item in weekly_spending:
                trends.append(
                    {
                        "date": item["week"].date()
                        if item["week"]
                        else self.start_date,
                        "amount": item["total_amount"] or Decimal("0.00"),
                    }
                )

        return trends

    def _get_monthly_trends(self):
        """Get monthly spending trends."""
        from django.db import connection
        from django.db.models.functions import Extract

        trends = []

        # SQLite doesn't support DATE_TRUNC, use alternative approach
        if connection.vendor == "sqlite":
            # Group by year and month for SQLite
            monthly_spending = (
                self.get_base_queryset()
                .annotate(year=Extract("date", "year"), month=Extract("date", "month"))
                .values("year", "month")
                .annotate(total_amount=Sum("amount_index"))
                .order_by("year", "month")
            )

            for item in monthly_spending:
                # Create date for first day of month
                year = item["year"]
                month = item["month"]
                from datetime import date

                month_start = date(year, month, 1)
                trends.append(
                    {
                        "date": month_start,
                        "amount": item["total_amount"] or Decimal("0.00"),
                    }
                )
        else:
            # PostgreSQL version with DATE_TRUNC
            monthly_spending = (
                self.get_base_queryset()
                .extra(
                    select={
                        "month": "DATE_TRUNC('month', date)",
                    }
                )
                .values("month")
                .annotate(total_amount=Sum("amount_index"))
                .order_by("month")
            )

            for item in monthly_spending:
                trends.append(
                    {
                        "date": item["month"].date()
                        if item["month"]
                        else self.start_date,
                        "amount": item["total_amount"] or Decimal("0.00"),
                    }
                )

        return trends

    def get_spending_comparison(self, comparison_start_date, comparison_end_date):
        """
        Compare spending between current period and comparison period.

        Args:
            comparison_start_date: Start date for comparison period
            comparison_end_date: End date for comparison period

        Returns:
            dict: Comparison data with current, comparison, change amounts and
                  percentage
        """
        current_spending = self.get_total_spending()

        # Create analytics for comparison period
        comparison_analytics = SpendingAnalytics(
            user=self.user,
            start_date=comparison_start_date,
            end_date=comparison_end_date,
        )
        comparison_spending = comparison_analytics.get_total_spending()

        # Calculate change
        change_amount = current_spending - comparison_spending

        if comparison_spending > 0:
            change_percentage = (change_amount / comparison_spending) * 100
        else:
            change_percentage = (
                Decimal("0.00") if change_amount == 0 else Decimal("100.00")
            )

        return {
            "current_period": current_spending,
            "comparison_period": comparison_spending,
            "change_amount": change_amount,
            "change_percentage": change_percentage.quantize(Decimal("0.01")),
        }

    def get_top_spending_categories(self, limit=5):
        """
        Get top spending categories for the period.

        Args:
            limit: Maximum number of categories to return

        Returns:
            list: List of dicts with category and amount keys
        """
        top_categories = []

        category_breakdown = self.get_category_breakdown()

        # Sort by amount descending and limit
        sorted_categories = sorted(
            category_breakdown.items(), key=lambda x: x[1], reverse=True
        )[:limit]

        for category_name, amount in sorted_categories:
            top_categories.append({"category": category_name, "amount": amount})

        return top_categories

    def get_transaction_count(self):
        """
        Get total number of transactions for the period.

        Returns:
            int: Number of transactions
        """
        return self.get_base_queryset().count()

    def get_average_transaction_amount(self):
        """
        Calculate average transaction amount for the period.

        Returns:
            Decimal: Average transaction amount
        """
        total_spending = self.get_total_spending()
        transaction_count = self.get_transaction_count()

        if transaction_count == 0:
            return Decimal("0.00")

        return total_spending / transaction_count

    def get_spending_by_day_of_week(self):
        """
        Get spending breakdown by day of the week.

        Returns:
            dict: Day of week (0=Monday) to total amount mapping
        """
        from django.db.models.functions import Extract

        spending_by_dow = {}

        dow_spending = (
            self.get_base_queryset()
            .annotate(day_of_week=Extract("date", "week_day"))
            .values("day_of_week")
            .annotate(total_amount=Sum("amount_index"))
        )

        # Initialize all days with zero
        day_names = {
            1: "Sunday",
            2: "Monday",
            3: "Tuesday",
            4: "Wednesday",
            5: "Thursday",
            6: "Friday",
            7: "Saturday",
        }

        for day_num, day_name in day_names.items():
            spending_by_dow[day_name] = Decimal("0.00")

        # Fill in actual spending data
        for item in dow_spending:
            day_num = item["day_of_week"]
            day_name = day_names.get(day_num, "Unknown")
            spending_by_dow[day_name] = item["total_amount"] or Decimal("0.00")

        return spending_by_dow
