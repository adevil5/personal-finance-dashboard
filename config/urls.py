"""
URL configuration for Personal Finance Dashboard project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
    # Django Allauth
    path("accounts/", include("allauth.urls")),
    # API endpoints
    path("api/v1/", include("apps.core.api_urls")),
    # App URLs
    path("", include("apps.core.urls")),
    path("expenses/", include("apps.expenses.urls")),
    path("budgets/", include("apps.budgets.urls")),
    path("analytics/", include("apps.analytics.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Django Debug Toolbar
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Custom error handlers
handler404 = "apps.core.views.custom_404"
handler500 = "apps.core.views.custom_500"
