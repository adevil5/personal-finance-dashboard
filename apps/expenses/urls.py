from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "expenses"

urlpatterns = [
    # Main transaction list view
    path(
        "",
        views.TransactionListView.as_view(),
        name="transaction-list",
    ),
    # Transaction creation form (placeholder)
    path(
        "create/",
        TemplateView.as_view(template_name="expenses/transaction_form.html"),
        name="transaction-create",
    ),
    # HTMX partial views
    path(
        "row/<int:pk>/",
        views.transaction_row_partial,
        name="transaction-row",
    ),
    path(
        "edit-form/<int:pk>/",
        views.transaction_edit_form_partial,
        name="transaction-edit-form",
    ),
    path(
        "update-htmx/<int:pk>/",
        views.transaction_update_htmx,
        name="transaction-update-htmx",
    ),
    path(
        "filter/",
        views.transaction_filter_partial,
        name="transaction-filter",
    ),
]
