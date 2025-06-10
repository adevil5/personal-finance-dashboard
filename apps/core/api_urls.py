from rest_framework import routers

from django.urls import include, path

from apps.budgets.views import BudgetViewSet
from apps.expenses.views import TransactionViewSet

app_name = "api"

# Create router for API endpoints
router = routers.DefaultRouter()
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"budgets", BudgetViewSet, basename="budget")

urlpatterns = [
    path("", include(router.urls)),
]
