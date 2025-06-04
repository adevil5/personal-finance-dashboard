"""
Admin configuration for core models.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import AuditLog, PIIAccessLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model."""

    list_display = (
        "timestamp",
        "user",
        "action",
        "resource_type",
        "resource_id",
        "ip_address",
        "is_archived",
    )
    list_filter = (
        "action",
        "resource_type",
        "is_archived",
        "timestamp",
    )
    search_fields = (
        "user__username",
        "user__email",
        "resource_id",
        "ip_address",
    )
    readonly_fields = (
        "timestamp",
        "user",
        "action",
        "resource_type",
        "resource_id",
        "ip_address",
        "user_agent",
        "metadata_display",
    )
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    def metadata_display(self, obj):
        """Display metadata in a formatted way."""
        if obj.metadata:
            import json

            formatted = json.dumps(obj.metadata, indent=2)
            return format_html("<pre>{}</pre>", formatted)
        return "-"

    metadata_display.short_description = "Metadata"

    def has_add_permission(self, request):
        """Prevent manual addition of audit logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete audit logs."""
        return request.user.is_superuser


@admin.register(PIIAccessLog)
class PIIAccessLogAdmin(admin.ModelAdmin):
    """Admin interface for PIIAccessLog model."""

    list_display = (
        "timestamp",
        "user",
        "pii_type",
        "action",
        "model_name",
        "field_name",
        "record_id",
        "ip_address",
    )
    list_filter = (
        "pii_type",
        "action",
        "model_name",
        "timestamp",
    )
    search_fields = (
        "user__username",
        "user__email",
        "record_id",
        "field_name",
        "ip_address",
    )
    readonly_fields = (
        "timestamp",
        "user",
        "pii_type",
        "action",
        "field_name",
        "model_name",
        "record_id",
        "ip_address",
        "accessed_value_hash",
        "access_reason",
    )
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        """Prevent manual addition of PII access logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete PII access logs."""
        return request.user.is_superuser

    def get_queryset(self, request):
        """Filter queryset based on user permissions."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Non-superusers can only see their own PII access logs
            qs = qs.filter(user=request.user)
        return qs
