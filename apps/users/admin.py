from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for the custom User model."""

    # Add custom fields to the user edit form
    fieldsets = BaseUserAdmin.fieldsets + (
        (_("Personal Info"), {"fields": ("phone",)}),
        (_("Preferences"), {"fields": ("timezone", "currency")}),
    )

    # Add custom fields to the user creation form
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_("Personal Info"), {"fields": ("phone",)}),
        (_("Preferences"), {"fields": ("timezone", "currency")}),
    )

    # Display custom fields in the list view
    list_display = BaseUserAdmin.list_display + ("phone", "timezone", "currency")

    # Make custom fields searchable
    search_fields = BaseUserAdmin.search_fields + ("phone",)

    # Allow filtering by currency and timezone
    list_filter = BaseUserAdmin.list_filter + ("currency", "timezone")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for the UserProfile model."""

    list_display = ("user", "monthly_income", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("user",)}),
        (
            _("Financial Information"),
            {
                "fields": ("monthly_income", "financial_goals"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
