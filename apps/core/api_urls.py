from rest_framework import routers

from django.urls import include, path

from apps.expenses.views import TransactionViewSet

app_name = "api"

# Create router for API endpoints
router = routers.DefaultRouter()
router.register(r"transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("", include(router.urls)),
]
