"""
Core models for the application.
"""

import hashlib
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLogManager(models.Manager):
    """Custom manager for AuditLog model."""

    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        request=None,
        user=None,
        metadata: Optional[dict] = None,
    ):
        """
        Convenience method to create audit log entries.

        Args:
            action: Action performed
            resource_type: Type of resource
            resource_id: ID of the resource
            request: Django request object (optional)
            user: User performing action (optional, extracted from request if provided)
            metadata: Additional metadata (optional)

        Returns:
            Created AuditLog instance
        """
        log_data = {
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
        }

        if request:
            log_data["user"] = getattr(request, "user", None)
            if log_data["user"] and log_data["user"].is_anonymous:
                log_data["user"] = None
            log_data["ip_address"] = request.META.get("REMOTE_ADDR")
            log_data["user_agent"] = request.META.get("HTTP_USER_AGENT")
        elif user:
            log_data["user"] = user

        return self.create(**log_data)

    def delete_old_logs(self, days: Optional[int] = None):
        """
        Delete audit logs older than specified days.

        Args:
            days: Number of days to retain logs (default from settings)

        Returns:
            Number of deleted logs
        """
        if days is None:
            days = getattr(settings, "AUDIT_LOG_RETENTION_DAYS", 365)

        cutoff_date = timezone.now() - timedelta(days=days)
        old_logs = self.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        old_logs.delete()
        return count

    def archive_old_logs(self, days: int = 90):
        """
        Archive old audit logs by marking them as archived.

        Args:
            days: Number of days after which to archive logs

        Returns:
            Number of archived logs
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(timestamp__lt=cutoff_date, is_archived=False).update(
            is_archived=True
        )


class AuditLog(models.Model):
    """
    General audit log for tracking all user actions in the system.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=50, db_index=True)
    resource_type = models.CharField(max_length=50, db_index=True)
    resource_id = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_archived = models.BooleanField(default=False)

    objects = AuditLogManager()

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["timestamp", "action"]),
        ]

    def __str__(self):
        username = self.user.username if self.user else "anonymous"
        return f"{username} - {self.action} - {self.resource_type}:{self.resource_id}"


class PIIAccessLogManager(models.Manager):
    """Custom manager for PIIAccessLog model."""

    def log_pii_access(
        self,
        pii_type: str,
        action: str,
        field_name: str,
        model_name: str,
        record_id: str,
        request=None,
        user=None,
        accessed_value: Optional[str] = None,
        access_reason: Optional[str] = None,
    ):
        """
        Log PII access event.

        Args:
            pii_type: Type of PII accessed
            action: Action performed on PII
            field_name: Name of the field containing PII
            model_name: Name of the model containing PII
            record_id: ID of the record containing PII
            request: Django request object (optional)
            user: User accessing PII (optional, extracted from request if provided)
            accessed_value: The actual PII value accessed (will be hashed)
            access_reason: Reason for accessing PII

        Returns:
            Created PIIAccessLog instance
        """
        log_data = {
            "pii_type": pii_type,
            "action": action,
            "field_name": field_name,
            "model_name": model_name,
            "record_id": record_id,
            "access_reason": access_reason,
        }

        if request:
            log_data["user"] = getattr(request, "user", None)
            if log_data["user"] and log_data["user"].is_anonymous:
                log_data["user"] = None
            log_data["ip_address"] = request.META.get("REMOTE_ADDR")
        elif user:
            log_data["user"] = user

        # Hash the accessed value if provided
        if accessed_value:
            log_data["accessed_value_hash"] = hashlib.sha256(
                accessed_value.encode()
            ).hexdigest()

        return self.create(**log_data)

    def delete_old_logs(self, days: Optional[int] = None):
        """
        Delete PII access logs older than specified days.
        PII logs have shorter retention period by default.

        Args:
            days: Number of days to retain logs (default from settings)

        Returns:
            Number of deleted logs
        """
        if days is None:
            days = getattr(settings, "PII_LOG_RETENTION_DAYS", 90)

        cutoff_date = timezone.now() - timedelta(days=days)
        old_logs = self.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        old_logs.delete()
        return count


class PIIAccessLog(models.Model):
    """
    Specialized audit log for tracking PII access.
    """

    PII_TYPE_CHOICES = [
        ("email", "Email Address"),
        ("phone", "Phone Number"),
        ("ssn", "Social Security Number"),
        ("credit_card", "Credit Card"),
        ("address", "Physical Address"),
        ("other", "Other PII"),
    ]

    ACTION_CHOICES = [
        ("view", "View"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("export", "Export"),
        ("decrypt", "Decrypt"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    pii_type = models.CharField(max_length=20, choices=PII_TYPE_CHOICES, db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    field_name = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100, db_index=True)
    record_id = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    accessed_value_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA256 hash of accessed value",
    )
    access_reason = models.TextField(null=True, blank=True)

    objects = PIIAccessLogManager()

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["pii_type", "timestamp"]),
            models.Index(fields=["model_name", "record_id"]),
        ]

    def __str__(self):
        username = self.user.username if self.user else "anonymous"
        return (
            f"{username} - {self.action} - {self.pii_type} - "
            f"{self.model_name}:{self.record_id}"
        )
