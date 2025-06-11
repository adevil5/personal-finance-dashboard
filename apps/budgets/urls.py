from django.urls import path
from django.views.generic import TemplateView

app_name = "budgets"

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="budgets/budget_list.html"),
        name="budget-list",
    ),
]
