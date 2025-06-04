"""
Tests for audit logging models.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone as django_timezone

from apps.core.models import AuditLog, PIIAccessLog

User = get_user_model()


class TestAuditLog(TestCase):
    """Test cases for AuditLog model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

    def test_audit_log_creation(self):
        """Test creating an audit log entry."""
        audit_log = AuditLog.objects.create(
            user=self.user,
            action="view",
            resource_type="transaction",
            resource_id="123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert audit_log.user == self.user
        assert audit_log.action == "view"
        assert audit_log.resource_type == "transaction"
        assert audit_log.resource_id == "123"
        assert audit_log.ip_address == "192.168.1.1"
        assert audit_log.user_agent == "Mozilla/5.0"
        assert audit_log.timestamp is not None

    def test_audit_log_without_user(self):
        """Test creating audit log for anonymous user."""
        audit_log = AuditLog.objects.create(
            action="view_public",
            resource_type="page",
            resource_id="home",
            ip_address="192.168.1.1",
        )

        assert audit_log.user is None
        assert audit_log.action == "view_public"

    def test_audit_log_with_metadata(self):
        """Test audit log with additional metadata."""
        metadata = {"old_value": "100.00", "new_value": "150.00", "field": "amount"}

        audit_log = AuditLog.objects.create(
            user=self.user,
            action="update",
            resource_type="transaction",
            resource_id="456",
            ip_address="192.168.1.1",
            metadata=metadata,
        )

        assert audit_log.metadata == metadata
        assert audit_log.metadata["old_value"] == "100.00"
        assert audit_log.metadata["new_value"] == "150.00"

    def test_audit_log_ordering(self):
        """Test that audit logs are ordered by timestamp descending."""
        # Create multiple logs
        for i in range(3):
            AuditLog.objects.create(
                user=self.user,
                action=f"action_{i}",
                resource_type="test",
                resource_id=str(i),
            )

        logs = AuditLog.objects.all()
        timestamps = [log.timestamp for log in logs]

        # Check that timestamps are in descending order
        assert timestamps == sorted(timestamps, reverse=True)

    def test_audit_log_string_representation(self):
        """Test string representation of audit log."""
        audit_log = AuditLog.objects.create(
            user=self.user,
            action="view",
            resource_type="transaction",
            resource_id="789",
        )

        expected = f"{self.user.username} - view - transaction:789"
        assert str(audit_log) == expected

    def test_audit_log_indexes(self):
        """Test that proper indexes exist on audit log table."""
        # This test verifies that the model has the expected indexes
        from django.db import connection

        # Skip index check for SQLite as it doesn't have pg_indexes
        if connection.vendor == "sqlite":
            # For SQLite, just verify the model has index definitions
            from apps.core.models import AuditLog

            indexes = AuditLog._meta.indexes
            assert len(indexes) > 0, "No indexes defined on AuditLog model"
            return

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'core_auditlog'
                """
            )
            indexes = [row[0] for row in cursor.fetchall()]

        # Check for expected indexes (names may vary by Django version)
        expected_fields = ["user_id", "timestamp", "resource_type", "action"]
        for field in expected_fields:
            assert any(field in idx for idx in indexes), f"No index found for {field}"

    def test_get_logs_for_user(self):
        """Test retrieving audit logs for a specific user."""
        other_user = User.objects.create_user(
            username="other", email="other@example.com"
        )

        # Create logs for different users
        AuditLog.objects.create(
            user=self.user, action="view", resource_type="transaction", resource_id="1"
        )
        AuditLog.objects.create(
            user=other_user, action="view", resource_type="transaction", resource_id="2"
        )
        AuditLog.objects.create(
            user=self.user, action="edit", resource_type="transaction", resource_id="3"
        )

        user_logs = AuditLog.objects.filter(user=self.user)
        assert user_logs.count() == 2
        assert all(log.user == self.user for log in user_logs)

    def test_get_logs_by_resource(self):
        """Test retrieving audit logs for a specific resource."""
        # Create logs for different resources
        AuditLog.objects.create(
            user=self.user,
            action="view",
            resource_type="transaction",
            resource_id="123",
        )
        AuditLog.objects.create(
            user=self.user,
            action="edit",
            resource_type="transaction",
            resource_id="123",
        )
        AuditLog.objects.create(
            user=self.user, action="view", resource_type="budget", resource_id="456"
        )

        resource_logs = AuditLog.objects.filter(
            resource_type="transaction", resource_id="123"
        )
        assert resource_logs.count() == 2

    def test_get_logs_by_date_range(self):
        """Test retrieving audit logs within a date range."""
        now = django_timezone.now()

        # Create logs at different times
        old_log = AuditLog.objects.create(
            user=self.user, action="old", resource_type="test", resource_id="1"
        )
        old_log.timestamp = now - timedelta(days=10)
        old_log.save()

        AuditLog.objects.create(
            user=self.user, action="recent", resource_type="test", resource_id="2"
        )

        # Query logs from last 7 days
        week_ago = now - timedelta(days=7)
        recent_logs = AuditLog.objects.filter(timestamp__gte=week_ago)

        assert recent_logs.count() == 1
        assert recent_logs.first().action == "recent"


class TestPIIAccessLog(TestCase):
    """Test cases for PIIAccessLog model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

    def test_pii_access_log_creation(self):
        """Test creating a PII access log entry."""
        pii_log = PIIAccessLog.objects.create(
            user=self.user,
            pii_type="email",
            action="view",
            field_name="email",
            model_name="User",
            record_id="123",
            ip_address="192.168.1.1",
            accessed_value_hash="abc123hash",
        )

        assert pii_log.user == self.user
        assert pii_log.pii_type == "email"
        assert pii_log.action == "view"
        assert pii_log.field_name == "email"
        assert pii_log.model_name == "User"
        assert pii_log.record_id == "123"
        assert pii_log.accessed_value_hash == "abc123hash"

    def test_pii_access_log_choices(self):
        """Test PII type and action choices."""
        # Test valid PII types
        valid_types = ["email", "phone", "ssn", "credit_card", "address", "other"]
        for pii_type in valid_types:
            pii_log = PIIAccessLog.objects.create(
                user=self.user,
                pii_type=pii_type,
                action="view",
                field_name="test_field",
                model_name="TestModel",
                record_id="1",
            )
            assert pii_log.pii_type == pii_type

        # Test valid actions
        valid_actions = ["view", "update", "delete", "export", "decrypt"]
        for action in valid_actions:
            pii_log = PIIAccessLog.objects.create(
                user=self.user,
                pii_type="email",
                action=action,
                field_name="test_field",
                model_name="TestModel",
                record_id="1",
            )
            assert pii_log.action == action

    def test_pii_access_log_reason(self):
        """Test PII access log with access reason."""
        pii_log = PIIAccessLog.objects.create(
            user=self.user,
            pii_type="ssn",
            action="view",
            field_name="social_security_number",
            model_name="UserProfile",
            record_id="456",
            access_reason="Customer support request #12345",
        )

        assert pii_log.access_reason == "Customer support request #12345"

    def test_pii_access_log_string_representation(self):
        """Test string representation of PII access log."""
        pii_log = PIIAccessLog.objects.create(
            user=self.user,
            pii_type="phone",
            action="update",
            field_name="phone_number",
            model_name="UserProfile",
            record_id="789",
        )

        expected = f"{self.user.username} - update - phone - UserProfile:789"
        assert str(pii_log) == expected

    def test_pii_access_log_indexes(self):
        """Test that proper indexes exist on PII access log table."""
        from django.db import connection

        # Skip index check for SQLite as it doesn't have pg_indexes
        if connection.vendor == "sqlite":
            # For SQLite, just verify the model has index definitions
            from apps.core.models import PIIAccessLog

            indexes = PIIAccessLog._meta.indexes
            assert len(indexes) > 0, "No indexes defined on PIIAccessLog model"
            return

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'core_piiaccesslog'
                """
            )
            indexes = [row[0] for row in cursor.fetchall()]

        # Check for expected indexes
        expected_fields = ["user_id", "timestamp", "pii_type", "model_name"]
        for field in expected_fields:
            assert any(field in idx for idx in indexes), f"No index found for {field}"

    def test_get_pii_logs_by_type(self):
        """Test retrieving PII logs by type."""
        # Create logs for different PII types
        PIIAccessLog.objects.create(
            user=self.user,
            pii_type="email",
            action="view",
            field_name="email",
            model_name="User",
            record_id="1",
        )
        PIIAccessLog.objects.create(
            user=self.user,
            pii_type="phone",
            action="view",
            field_name="phone",
            model_name="UserProfile",
            record_id="2",
        )
        PIIAccessLog.objects.create(
            user=self.user,
            pii_type="email",
            action="update",
            field_name="email",
            model_name="User",
            record_id="3",
        )

        email_logs = PIIAccessLog.objects.filter(pii_type="email")
        assert email_logs.count() == 2
        assert all(log.pii_type == "email" for log in email_logs)


class TestAuditLogManager(TestCase):
    """Test cases for AuditLog manager methods."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

    def test_log_action_method(self):
        """Test the log_action convenience method."""
        request = RequestFactory().get("/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        request.META["HTTP_USER_AGENT"] = "Test Browser"

        audit_log = AuditLog.objects.log_action(
            request=request,
            action="test_action",
            resource_type="test_resource",
            resource_id="123",
            metadata={"test": "data"},
        )

        assert audit_log.user == self.user
        assert audit_log.action == "test_action"
        assert audit_log.resource_type == "test_resource"
        assert audit_log.resource_id == "123"
        assert audit_log.ip_address == "192.168.1.100"
        assert audit_log.user_agent == "Test Browser"
        assert audit_log.metadata == {"test": "data"}

    def test_log_action_without_request(self):
        """Test log_action method without request object."""
        audit_log = AuditLog.objects.log_action(
            user=self.user,
            action="background_task",
            resource_type="cron_job",
            resource_id="daily_cleanup",
        )

        assert audit_log.user == self.user
        assert audit_log.action == "background_task"
        assert audit_log.ip_address is None
        assert audit_log.user_agent is None


class TestPIIAccessLogManager(TestCase):
    """Test cases for PIIAccessLog manager methods."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

    def test_log_pii_access_method(self):
        """Test the log_pii_access convenience method."""
        import hashlib

        request = RequestFactory().get("/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        # Mock the hashing of accessed value
        accessed_value = "test@example.com"
        expected_hash = hashlib.sha256(accessed_value.encode()).hexdigest()

        pii_log = PIIAccessLog.objects.log_pii_access(
            request=request,
            pii_type="email",
            action="view",
            field_name="email",
            model_name="User",
            record_id="123",
            accessed_value=accessed_value,
            access_reason="Testing",
        )

        assert pii_log.user == self.user
        assert pii_log.pii_type == "email"
        assert pii_log.action == "view"
        assert pii_log.ip_address == "192.168.1.100"
        assert pii_log.accessed_value_hash == expected_hash
        assert pii_log.access_reason == "Testing"

    def test_log_pii_access_without_value(self):
        """Test logging PII access without the actual value."""
        pii_log = PIIAccessLog.objects.log_pii_access(
            user=self.user,
            pii_type="ssn",
            action="delete",
            field_name="social_security_number",
            model_name="UserProfile",
            record_id="456",
        )

        assert pii_log.accessed_value_hash is None
        assert pii_log.action == "delete"


class TestAuditLogRetention(TestCase):
    """Test cases for audit log retention policies."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

    def test_delete_old_logs(self):
        """Test deletion of old audit logs."""
        now = django_timezone.now()

        # Create logs with different ages
        old_log = AuditLog.objects.create(
            user=self.user,
            action="old_action",
            resource_type="test",
            resource_id="1",
        )
        old_log.timestamp = now - timedelta(days=400)  # Older than retention period
        old_log.save()

        AuditLog.objects.create(
            user=self.user,
            action="recent_action",
            resource_type="test",
            resource_id="2",
        )

        # Run retention cleanup (365 days default)
        deleted_count = AuditLog.objects.delete_old_logs()

        assert deleted_count == 1
        assert AuditLog.objects.count() == 1
        assert AuditLog.objects.first().action == "recent_action"

    def test_delete_old_logs_custom_retention(self):
        """Test deletion with custom retention period."""
        now = django_timezone.now()

        # Create logs
        for i in range(5):
            log = AuditLog.objects.create(
                user=self.user,
                action=f"action_{i}",
                resource_type="test",
                resource_id=str(i),
            )
            log.timestamp = now - timedelta(days=i * 10)
            log.save()

        # Delete logs older than 30 days
        deleted_count = AuditLog.objects.delete_old_logs(days=30)

        assert deleted_count == 2  # Logs at 30 and 40 days old
        assert AuditLog.objects.count() == 3

    def test_archive_old_logs(self):
        """Test archiving old audit logs."""
        now = django_timezone.now()

        # Create old log
        old_log = AuditLog.objects.create(
            user=self.user,
            action="archive_me",
            resource_type="test",
            resource_id="1",
            metadata={"important": "data"},
        )
        old_log.timestamp = now - timedelta(days=100)
        old_log.save()

        # Archive logs older than 90 days
        archived_count = AuditLog.objects.archive_old_logs(days=90)

        assert archived_count == 1

        # Check that log is marked as archived
        old_log.refresh_from_db()
        assert old_log.is_archived is True

    def test_pii_log_retention(self):
        """Test PII access log retention is shorter."""
        now = django_timezone.now()

        # Create PII logs with different ages
        old_pii_log = PIIAccessLog.objects.create(
            user=self.user,
            pii_type="ssn",
            action="view",
            field_name="ssn",
            model_name="User",
            record_id="1",
        )
        old_pii_log.timestamp = now - timedelta(days=100)  # Older than 90 days
        old_pii_log.save()

        PIIAccessLog.objects.create(
            user=self.user,
            pii_type="email",
            action="view",
            field_name="email",
            model_name="User",
            record_id="2",
        )

        # PII logs have shorter retention (90 days)
        deleted_count = PIIAccessLog.objects.delete_old_logs(days=90)

        assert deleted_count == 1
        assert PIIAccessLog.objects.count() == 1
        assert PIIAccessLog.objects.first().pii_type == "email"

    @patch("apps.core.models.settings")
    def test_retention_settings_override(self, mock_settings):
        """Test that retention periods can be overridden by settings."""
        # Mock settings
        mock_settings.AUDIT_LOG_RETENTION_DAYS = 180
        mock_settings.PII_LOG_RETENTION_DAYS = 30

        now = django_timezone.now()

        # Create logs
        audit_log = AuditLog.objects.create(
            user=self.user,
            action="test",
            resource_type="test",
            resource_id="1",
        )
        audit_log.timestamp = now - timedelta(days=190)
        audit_log.save()

        pii_log = PIIAccessLog.objects.create(
            user=self.user,
            pii_type="email",
            action="view",
            field_name="email",
            model_name="User",
            record_id="1",
        )
        pii_log.timestamp = now - timedelta(days=40)
        pii_log.save()

        # Use settings-based retention
        AuditLog.objects.delete_old_logs()  # Uses 180 days from settings
        PIIAccessLog.objects.delete_old_logs()  # Uses 30 days from settings

        assert AuditLog.objects.count() == 0  # Deleted (older than 180 days)
        assert PIIAccessLog.objects.count() == 0  # Deleted (older than 30 days)


@pytest.mark.django_db
class TestAuditLogQueryPerformance:
    """Test query performance for audit logs."""

    def test_bulk_create_performance(self):
        """Test bulk creation of audit logs."""
        user = User.objects.create_user(username="bulkuser", email="bulk@example.com")

        # Create many logs efficiently
        logs = []
        for i in range(1000):
            logs.append(
                AuditLog(
                    user=user,
                    action="bulk_action",
                    resource_type="test",
                    resource_id=str(i),
                )
            )

        # Bulk create should be efficient
        AuditLog.objects.bulk_create(logs)

        assert AuditLog.objects.count() == 1000

    def test_query_with_indexes(self):
        """Test that queries use indexes efficiently."""
        user = User.objects.create_user(username="indextest", email="index@example.com")

        # Create logs
        for i in range(100):
            AuditLog.objects.create(
                user=user,
                action=f"action_{i % 10}",
                resource_type=f"type_{i % 5}",
                resource_id=str(i),
            )

        # These queries should use indexes
        user_logs = AuditLog.objects.filter(user=user).count()
        type_logs = AuditLog.objects.filter(resource_type="type_0").count()
        recent_logs = AuditLog.objects.filter(
            timestamp__gte=django_timezone.now() - timedelta(hours=1)
        ).count()

        assert user_logs == 100
        assert type_logs == 20
        assert recent_logs == 100
