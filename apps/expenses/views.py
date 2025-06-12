from decimal import Decimal

from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, ListView

from .forms import TransactionForm
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


# Frontend Views


class TransactionCreateView(LoginRequiredMixin, CreateView):
    """
    Frontend view for creating new transactions.
    
    Features:
    - User-scoped transaction creation
    - Form validation with proper error handling
    - Receipt file upload support
    - Category selection with dynamic visibility
    - HTMX support for dynamic updates
    """
    
    model = Transaction
    form_class = TransactionForm
    template_name = 'expenses/transaction_form.html'
    success_url = reverse_lazy('expenses:transaction-list')
    
    def get_form_kwargs(self):
        """Add user to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Add additional context data for the template."""
        context = super().get_context_data(**kwargs)
        
        # Add user's categories for the form
        context['categories'] = Category.objects.filter(
            user=self.request.user, is_active=True
        ).order_by('name')
        
        return context
    
    def form_valid(self, form):
        """Handle successful form submission."""
        # The form's save method already sets the user and handles validation
        response = super().form_valid(form)
        
        # For HTMX requests, return a success message or redirect
        if self.request.headers.get('HX-Request'):
            from django.contrib import messages
            messages.success(self.request, 'Transaction created successfully!')
            return render(self.request, 'expenses/_transaction_success.html', {
                'transaction': self.object
            })
        
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        # For HTMX requests, return the form with errors
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'expenses/transaction_form.html', {
                'form': form
            })
        
        return super().form_invalid(form)


class TransactionListView(LoginRequiredMixin, ListView):
    """
    Frontend view for displaying paginated list of transactions.

    Features:
    - User-scoped transactions only
    - Pagination (20 items per page)
    - Search functionality (description, merchant, notes)
    - Filtering by category, date range, amount range, type
    - Ordering by date (newest first)
    """

    model = Transaction
    template_name = "expenses/transaction_list.html"
    context_object_name = "transactions"
    paginate_by = 20

    def get_queryset(self):
        """Return filtered and ordered transactions for the current user."""
        queryset = (
            Transaction.objects.filter(user=self.request.user, is_active=True)
            .select_related("category", "parent_transaction")
            .order_by("-date", "-created_at")
        )

        # Apply search filter
        search_query = self.request.GET.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(description__icontains=search_query)
                | Q(merchant__icontains=search_query)
                | Q(notes__icontains=search_query)
            )

        # Apply category filter
        category_id = self.request.GET.get("category")
        if category_id:
            try:
                queryset = queryset.filter(category_id=int(category_id))
            except (ValueError, TypeError):
                pass

        # Apply date range filters
        date_after = self.request.GET.get("date_after")
        if date_after:
            try:
                queryset = queryset.filter(date__gte=date_after)
            except ValueError:
                pass

        date_before = self.request.GET.get("date_before")
        if date_before:
            try:
                queryset = queryset.filter(date__lte=date_before)
            except ValueError:
                pass

        # Apply amount range filters
        amount_min = self.request.GET.get("amount_min")
        if amount_min:
            try:
                queryset = queryset.filter(amount_index__gte=Decimal(amount_min))
            except (ValueError, TypeError):
                pass

        amount_max = self.request.GET.get("amount_max")
        if amount_max:
            try:
                queryset = queryset.filter(amount_index__lte=Decimal(amount_max))
            except (ValueError, TypeError):
                pass

        # Apply transaction type filter
        transaction_type = self.request.GET.get("transaction_type")
        if transaction_type in [
            Transaction.EXPENSE,
            Transaction.INCOME,
            Transaction.TRANSFER,
        ]:
            queryset = queryset.filter(transaction_type=transaction_type)

        return queryset

    def get_context_data(self, **kwargs):
        """Add additional context data for the template."""
        context = super().get_context_data(**kwargs)

        # Add user's categories for filter dropdown
        context["categories"] = Category.objects.filter(
            user=self.request.user, is_active=True
        ).order_by("name")

        # Add current filter values to context
        context["search_query"] = self.request.GET.get("search", "")
        context["selected_category"] = self.request.GET.get("category", "")
        context["date_after"] = self.request.GET.get("date_after", "")
        context["date_before"] = self.request.GET.get("date_before", "")
        context["amount_min"] = self.request.GET.get("amount_min", "")
        context["amount_max"] = self.request.GET.get("amount_max", "")
        context["transaction_type"] = self.request.GET.get("transaction_type", "")

        # Add transaction type choices for filter dropdown
        context["transaction_types"] = Transaction.TRANSACTION_TYPE_CHOICES

        return context


@login_required
def transaction_row_partial(request, pk):
    """
    HTMX partial view for rendering a single transaction row.
    Used for updating individual rows after inline editing.
    """
    transaction = get_object_or_404(
        Transaction, pk=pk, user=request.user, is_active=True
    )
    return render(
        request, "expenses/_transaction_row.html", {"transaction": transaction}
    )


@login_required
def transaction_edit_form_partial(request, pk):
    """
    HTMX partial view for rendering transaction edit form.
    Used for inline editing functionality.
    """
    transaction = get_object_or_404(
        Transaction, pk=pk, user=request.user, is_active=True
    )
    categories = Category.objects.filter(user=request.user, is_active=True).order_by(
        "name"
    )

    return render(
        request,
        "expenses/_transaction_edit_form.html",
        {
            "transaction": transaction,
            "categories": categories,
            "transaction_types": Transaction.TRANSACTION_TYPE_CHOICES,
        },
    )


@login_required
@require_http_methods(["POST"])
def transaction_update_htmx(request, pk):
    """
    HTMX view for updating a transaction via inline editing.
    Returns the updated transaction row on success.
    """
    transaction = get_object_or_404(
        Transaction, pk=pk, user=request.user, is_active=True
    )

    try:
        # Update transaction fields
        transaction.description = request.POST.get("description", "").strip()
        transaction.merchant = request.POST.get("merchant", "").strip()
        transaction.notes = request.POST.get("notes", "").strip()

        # Handle amount
        amount_str = request.POST.get("amount", "").strip()
        if amount_str:
            transaction.amount = Decimal(amount_str)
            # Update amount_index for filtering/sorting
            transaction.amount_index = transaction.amount

        # Handle date
        date_str = request.POST.get("date", "").strip()
        if date_str:
            from datetime import datetime

            transaction.date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Handle category (only for expenses)
        if transaction.transaction_type == Transaction.EXPENSE:
            category_id = request.POST.get("category")
            if category_id:
                try:
                    category = Category.objects.get(
                        id=int(category_id), user=request.user, is_active=True
                    )
                    transaction.category = category
                except (Category.DoesNotExist, ValueError, TypeError):
                    return JsonResponse(
                        {"error": "Invalid category selected"}, status=400
                    )

        # Handle transaction type
        transaction_type = request.POST.get("transaction_type")
        if transaction_type in [
            Transaction.EXPENSE,
            Transaction.INCOME,
            Transaction.TRANSFER,
        ]:
            transaction.transaction_type = transaction_type
            # Clear category for non-expense transactions
            if transaction_type != Transaction.EXPENSE:
                transaction.category = None

        transaction.save()

        # Return updated transaction row
        return render(
            request, "expenses/_transaction_row.html", {"transaction": transaction}
        )

    except Decimal.InvalidOperation:
        return JsonResponse({"error": "Invalid amount format"}, status=400)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception:
        return JsonResponse({"error": "An error occurred while updating"}, status=500)


@login_required
def transaction_filter_partial(request):
    """
    HTMX partial view for filtering transactions.
    Returns filtered transaction list without page reload.
    """
    # Use the same filtering logic as TransactionListView
    queryset = (
        Transaction.objects.filter(user=request.user, is_active=True)
        .select_related("category", "parent_transaction")
        .order_by("-date", "-created_at")
    )

    # Apply search filter
    search_query = request.GET.get("search", "").strip()
    if search_query:
        queryset = queryset.filter(
            Q(description__icontains=search_query)
            | Q(merchant__icontains=search_query)
            | Q(notes__icontains=search_query)
        )

    # Apply category filter
    category_id = request.GET.get("category")
    if category_id:
        try:
            queryset = queryset.filter(category_id=int(category_id))
        except (ValueError, TypeError):
            pass

    # Apply date range filters
    date_after = request.GET.get("date_after")
    if date_after:
        try:
            queryset = queryset.filter(date__gte=date_after)
        except ValueError:
            pass

    date_before = request.GET.get("date_before")
    if date_before:
        try:
            queryset = queryset.filter(date__lte=date_before)
        except ValueError:
            pass

    # Apply amount range filters
    amount_min = request.GET.get("amount_min")
    if amount_min:
        try:
            queryset = queryset.filter(amount_index__gte=Decimal(amount_min))
        except (ValueError, TypeError):
            pass

    amount_max = request.GET.get("amount_max")
    if amount_max:
        try:
            queryset = queryset.filter(amount_index__lte=Decimal(amount_max))
        except (ValueError, TypeError):
            pass

    # Apply transaction type filter
    transaction_type = request.GET.get("transaction_type")
    if transaction_type in [
        Transaction.EXPENSE,
        Transaction.INCOME,
        Transaction.TRANSFER,
    ]:
        queryset = queryset.filter(transaction_type=transaction_type)

    # Apply pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "expenses/_transaction_list_partial.html",
        {
            "transactions": page_obj,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
        },
    )
