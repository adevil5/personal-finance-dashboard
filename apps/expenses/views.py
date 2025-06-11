from decimal import Decimal

from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.http import Http404

from .models import Category, Transaction
from .serializers import (
    TransactionBulkDeleteSerializer,
    TransactionBulkUpdateSerializer,
    TransactionCSVImportSerializer,
    TransactionSerializer,
    TransactionStatisticsSerializer,
)
from .utils import get_user_receipt_url, get_user_storage_usage


class TransactionFilter(filters.FilterSet):
    """Filter class for Transaction queries."""

    transaction_type = filters.ChoiceFilter(
        choices=Transaction.TRANSACTION_TYPE_CHOICES
    )
    category = filters.NumberFilter(field_name="category__id")
    date_after = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_before = filters.DateFilter(field_name="date", lookup_expr="lte")
    amount_min = filters.NumberFilter(field_name="amount_index", lookup_expr="gte")
    amount_max = filters.NumberFilter(field_name="amount_index", lookup_expr="lte")
    is_recurring = filters.BooleanFilter()

    class Meta:
        model = Transaction
        fields = [
            "transaction_type",
            "category",
            "date_after",
            "date_before",
            "amount_min",
            "amount_max",
            "is_recurring",
        ]


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Transaction CRUD operations.

    Provides endpoints for:
    - List transactions (with filtering, search, ordering, pagination)
    - Create single or bulk transactions
    - Retrieve, update, and delete transactions
    - Get transaction statistics

    All operations are scoped to the authenticated user.
    """

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = TransactionFilter
    search_fields = ["description", "merchant", "notes"]
    ordering_fields = ["date", "created_at", "amount_index"]
    ordering = ["-date", "-created_at"]  # Default ordering

    def get_queryset(self):
        """Return transactions for the current user only."""
        return Transaction.objects.filter(
            user=self.request.user, is_active=True
        ).select_related("category", "parent_transaction")

    def perform_destroy(self, instance):
        """Soft delete by setting is_active to False."""
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        """Bulk create multiple transactions."""
        created_transactions = []
        for transaction_data in request.data.get("transactions", []):
            serializer = TransactionSerializer(
                data=transaction_data, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            transaction = serializer.save()
            created_transactions.append(transaction)

        # Serialize the created transactions
        transaction_serializer = TransactionSerializer(
            created_transactions, many=True, context={"request": request}
        )

        return Response(
            {"transactions": transaction_serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        Get transaction statistics for the current user.

        Accepts optional query parameters:
        - date_from: Start date for statistics
        - date_to: End date for statistics
        """
        queryset = self.get_queryset()

        # Apply date filtering if provided
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        # Calculate statistics in Python since encrypted fields can't use aggregation
        expenses = queryset.filter(transaction_type=Transaction.EXPENSE)
        income = queryset.filter(transaction_type=Transaction.INCOME)

        # Calculate totals in Python
        total_expenses = sum(expense.amount for expense in expenses) or Decimal("0")
        total_income = sum(inc.amount for inc in income) or Decimal("0")

        # Category breakdown for expenses
        category_breakdown = {}
        for expense in expenses:
            if expense.category and expense.category.name:
                category_name = expense.category.name
                if category_name not in category_breakdown:
                    category_breakdown[category_name] = Decimal("0")
                category_breakdown[category_name] += expense.amount

        # Convert to strings for JSON serialization
        for name, amount in category_breakdown.items():
            category_breakdown[name] = str(amount)

        # Prepare response data
        data = {
            "total_expenses": str(total_expenses),
            "total_income": str(total_income),
            "net_amount": str(total_income - total_expenses),
            "transaction_count": queryset.count(),
            "expense_count": expenses.count(),
            "income_count": income.count(),
            "category_breakdown": category_breakdown,
        }

        if date_from:
            data["date_from"] = date_from
        if date_to:
            data["date_to"] = date_to

        serializer = TransactionStatisticsSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        """Import transactions from CSV/Excel file."""
        import csv
        import io
        from decimal import Decimal, InvalidOperation

        serializer = TransactionCSVImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]

        try:
            # Handle different file types
            if uploaded_file.name.lower().endswith(".csv"):
                # CSV file handling
                file_content = uploaded_file.read().decode("utf-8")
                csv_reader = csv.DictReader(io.StringIO(file_content))
            elif uploaded_file.name.lower().endswith((".xlsx", ".xls")):
                # Excel file handling
                import openpyxl

                workbook = openpyxl.load_workbook(uploaded_file)
                sheet = workbook.active

                # Get headers from first row
                headers = [cell.value for cell in sheet[1]]
                csv_reader = []

                # Convert Excel rows to dictionary format
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    row_dict = dict(zip(headers, row))
                    csv_reader.append(row_dict)

            imported_count = 0
            errors = []

            for row_number, row in enumerate(csv_reader, start=2):
                try:
                    # Clean and prepare data
                    transaction_data = {}

                    # Required fields
                    if row.get("date"):
                        from datetime import datetime

                        if isinstance(row["date"], str):
                            transaction_data["date"] = datetime.strptime(
                                row["date"], "%Y-%m-%d"
                            ).date()
                        else:
                            transaction_data["date"] = row["date"]

                    if row.get("amount"):
                        try:
                            transaction_data["amount"] = Decimal(str(row["amount"]))
                        except (InvalidOperation, ValueError):
                            raise ValueError(f"Invalid amount: {row['amount']}")

                    transaction_data["description"] = row.get("description", "")
                    transaction_data["transaction_type"] = row.get(
                        "transaction_type", "expense"
                    )
                    transaction_data["merchant"] = row.get("merchant", "")
                    transaction_data["notes"] = row.get("notes", "")

                    # Handle category by name
                    category_name = row.get("category_name", "").strip()
                    if (
                        category_name
                        and transaction_data["transaction_type"] == "expense"
                    ):
                        try:
                            category = Category.objects.get(
                                user=request.user, name=category_name, is_active=True
                            )
                            transaction_data["category_id"] = category.id
                        except Category.DoesNotExist:
                            raise ValueError(f"Category '{category_name}' not found")

                    # Validate using serializer
                    transaction_serializer = TransactionSerializer(
                        data=transaction_data, context={"request": request}
                    )
                    transaction_serializer.is_valid(raise_exception=True)
                    transaction_serializer.save()
                    imported_count += 1

                except Exception as e:
                    errors.append(
                        {
                            "row": row_number,
                            "error": str(e),
                            "data": dict(row) if hasattr(row, "items") else row,
                        }
                    )

            # Return response based on results
            if errors and imported_count == 0:
                return Response(
                    {"errors": errors, "imported_count": 0},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif errors:
                return Response(
                    {"imported_count": imported_count, "errors": errors},
                    status=status.HTTP_207_MULTI_STATUS,
                )
            else:
                return Response(
                    {"imported_count": imported_count}, status=status.HTTP_201_CREATED
                )

        except Exception as e:
            return Response(
                {"error": f"File processing error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"], url_path="import-excel")
    def import_excel(self, request):
        """Import transactions from Excel file specifically."""
        # Reuse the CSV import method since it handles Excel files
        return self.import_csv(request)

    @action(detail=False, methods=["patch"], url_path="bulk-update")
    def bulk_update(self, request):
        """Bulk update multiple transactions."""
        serializer = TransactionBulkUpdateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        updates = serializer.validated_data["updates"]
        updated_count = 0
        errors = []

        for update_data in updates:
            transaction_id = update_data.pop("id")
            try:
                transaction = Transaction.objects.get(
                    id=transaction_id, user=request.user, is_active=True
                )

                # Update fields
                for field, value in update_data.items():
                    if field == "category_id":
                        transaction.category = value
                    else:
                        setattr(transaction, field, value)

                transaction.save()
                updated_count += 1

            except Transaction.DoesNotExist:
                errors.append(
                    {"transaction_id": transaction_id, "error": "Transaction not found"}
                )
            except Exception as e:
                errors.append({"transaction_id": transaction_id, "error": str(e)})

        response_data = {"updated_count": updated_count}
        if errors:
            response_data["errors"] = errors

        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"], url_path="bulk-delete")
    def bulk_delete(self, request):
        """Bulk delete (soft delete) multiple transactions."""
        serializer = TransactionBulkDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transaction_ids = serializer.validated_data["transaction_ids"]

        # Only delete user's own transactions
        deleted_count = Transaction.objects.filter(
            id__in=transaction_ids, user=request.user, is_active=True
        ).update(is_active=False)

        return Response({"deleted_count": deleted_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="receipt-url")
    def get_receipt_url(self, request, pk=None):
        """
        Get a secure pre-signed URL for accessing transaction receipt.

        Args:
            expires_in (int): Optional URL expiration time in seconds (default: 3600)

        Returns:
            Response with pre-signed URL or error message
        """
        try:
            # Get expiration time from query params (default 1 hour)
            expires_in = int(request.query_params.get("expires_in", 3600))

            # Validate expiration time (max 24 hours)
            if expires_in > 86400:  # 24 hours
                expires_in = 86400
            elif expires_in < 60:  # Minimum 1 minute
                expires_in = 60

            # Get secure URL for the receipt
            url = get_user_receipt_url(pk, request.user, expires_in)

            if url:
                return Response(
                    {
                        "receipt_url": url,
                        "expires_in": expires_in,
                        "transaction_id": pk,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "No receipt found for this transaction"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Http404:
            return Response(
                {"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {"error": f"Invalid parameter: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to generate receipt URL: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="storage-usage")
    def get_storage_usage(self, request):
        """
        Get storage usage statistics for the current user.

        Returns:
            Response with storage usage information
        """
        try:
            usage_stats = get_user_storage_usage(request.user)

            return Response(
                {"user_id": request.user.id, "storage_usage": usage_stats},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to get storage usage: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
