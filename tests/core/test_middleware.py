"""
Tests for audit middleware.
"""

from unittest.mock import Mock, patch

import pytest

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.core.middleware import PIIAuditMiddleware
from apps.core.models import AuditLog

User = get_user_model()


class TestPIIAuditMiddleware(TestCase):
    """Test cases for PIIAuditMiddleware."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.middleware = PIIAuditMiddleware(
            get_response=Mock(return_value=HttpResponse())
        )
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

    def test_middleware_processes_request(self):
        """Test that middleware processes requests correctly."""
        request = self.factory.get("/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Test Browser"

        response = self.middleware(request)

        assert response.status_code == 200
        assert hasattr(request, "_pii_audit_context")

    def test_middleware_sets_audit_context(self):
        """Test that middleware sets audit context on request."""
        request = self.factory.get("/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        context = request._pii_audit_context
        assert context["user"] == self.user
        assert context["ip_address"] == "192.168.1.1"
        assert context["request_path"] == "/test/"

    def test_middleware_handles_anonymous_user(self):
        """Test middleware with anonymous user."""
        request = self.factory.get("/test/")
        request.user = Mock()
        request.user.is_anonymous = True
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        context = request._pii_audit_context
        assert context["user"] is None

    def test_middleware_extracts_ip_from_headers(self):
        """Test IP extraction from various headers."""
        # Test X-Forwarded-For header
        request = self.factory.get("/test/")
        request.user = self.user
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 198.51.100.1"
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        context = request._pii_audit_context
        assert context["ip_address"] == "203.0.113.1"

    def test_middleware_extracts_ip_from_real_ip_header(self):
        """Test IP extraction from X-Real-IP header."""
        request = self.factory.get("/test/")
        request.user = self.user
        request.META["HTTP_X_REAL_IP"] = "203.0.113.5"
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        context = request._pii_audit_context
        assert context["ip_address"] == "203.0.113.5"

    def test_middleware_fallback_to_remote_addr(self):
        """Test fallback to REMOTE_ADDR when no proxy headers."""
        request = self.factory.get("/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        context = request._pii_audit_context
        assert context["ip_address"] == "192.168.1.1"

    def test_middleware_handles_missing_ip(self):
        """Test middleware when IP address is not available."""
        request = self.factory.get("/test/")
        request.user = self.user
        # Remove REMOTE_ADDR if it was set by RequestFactory
        if "REMOTE_ADDR" in request.META:
            del request.META["REMOTE_ADDR"]

        self.middleware(request)

        context = getattr(request, "_pii_audit_context")
        assert context["ip_address"] is None

    def test_log_user_action_method(self):
        """Test the log_user_action method."""
        request = self.factory.post("/test/action/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Test Browser"

        self.middleware(request)

        # Use the middleware method to log an action
        audit_log = self.middleware.log_user_action(
            request=request,
            action="create",
            resource_type="transaction",
            resource_id="123",
            metadata={"amount": "50.00"},
        )

        assert audit_log.user == self.user
        assert audit_log.action == "create"
        assert audit_log.resource_type == "transaction"
        assert audit_log.resource_id == "123"
        assert audit_log.ip_address == "192.168.1.1"
        assert audit_log.user_agent == "Test Browser"
        assert audit_log.metadata == {"amount": "50.00"}

    def test_log_pii_access_method(self):
        """Test the log_pii_access method."""
        request = self.factory.get("/user/profile/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        # Use the middleware method to log PII access
        pii_log = self.middleware.log_pii_access(
            request=request,
            pii_type="email",
            action="view",
            field_name="email",
            model_name="User",
            record_id="123",
            accessed_value="test@example.com",
            access_reason="Profile view",
        )

        assert pii_log.user == self.user
        assert pii_log.pii_type == "email"
        assert pii_log.action == "view"
        assert pii_log.field_name == "email"
        assert pii_log.model_name == "User"
        assert pii_log.record_id == "123"
        assert pii_log.ip_address == "192.168.1.1"
        assert pii_log.access_reason == "Profile view"
        assert pii_log.accessed_value_hash is not None

    def test_automatic_action_logging_for_sensitive_views(self):
        """Test automatic logging for views that access user data."""
        request = self.factory.get("/users/profile/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Test Browser"

        # Mock the response to simulate a view execution
        def mock_get_response(req):
            # Simulate logging during view execution
            self.middleware.log_user_action(
                request=req,
                action="view",
                resource_type="user_profile",
                resource_id=str(req.user.id),
            )
            return HttpResponse("Profile page")

        middleware = PIIAuditMiddleware(get_response=mock_get_response)
        response = middleware(request)

        assert response.status_code == 200

        # Check that audit log was created
        audit_logs = AuditLog.objects.filter(
            user=self.user, action="view", resource_type="user_profile"
        )
        assert audit_logs.count() == 1

    def test_middleware_thread_safety(self):
        """Test that middleware is thread-safe."""
        import threading
        from threading import Lock

        results = []
        results_lock = Lock()

        def make_request(thread_id):
            # Create a mock user without database operations
            from unittest.mock import Mock

            user = Mock()
            user.id = thread_id + 100
            user.is_anonymous = False

            request = self.factory.get(f"/test/{thread_id}/")
            request.user = user
            request.META["REMOTE_ADDR"] = f"192.168.1.{thread_id}"

            self.middleware(request)

            context = getattr(request, "_pii_audit_context")
            with results_lock:
                results.append(
                    {
                        "thread_id": thread_id,
                        "ip": context["ip_address"],
                        "path": context["request_path"],
                        "user": context["user"],
                    }
                )

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i + 10,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each request was processed correctly
        assert len(results) == 5
        # Sort results by thread_id for predictable comparison
        results.sort(key=lambda x: x["thread_id"])
        for i, result in enumerate(results):
            expected_thread_id = i + 10
            assert result["ip"] == f"192.168.1.{expected_thread_id}"
            assert result["path"] == f"/test/{expected_thread_id}/"
            assert result["user"] is not None

    def test_middleware_handles_exceptions(self):
        """Test middleware handles exceptions gracefully."""

        def failing_get_response(request):
            raise ValueError("Something went wrong")

        middleware = PIIAuditMiddleware(get_response=failing_get_response)
        request = self.factory.get("/test/")
        request.user = self.user

        # Should not raise exception
        with pytest.raises(ValueError):
            middleware(request)

        # Context should still be set even if response fails
        assert hasattr(request, "_pii_audit_context")

    def test_middleware_performance_with_large_requests(self):
        """Test middleware performance with large request data."""
        # Create a request with large POST data
        large_data = {"data": "x" * 10000}  # 10KB of data

        request = self.factory.post("/test/", data=large_data)
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        import time

        start_time = time.time()

        self.middleware(request)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process quickly (less than 100ms)
        assert processing_time < 0.1
        assert hasattr(request, "_pii_audit_context")

    def test_log_bulk_actions(self):
        """Test logging bulk actions efficiently."""
        request = self.factory.post("/bulk-update/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        # Simulate bulk operation
        resource_ids = [str(i) for i in range(10)]

        for resource_id in resource_ids:
            self.middleware.log_user_action(
                request=request,
                action="bulk_update",
                resource_type="transaction",
                resource_id=resource_id,
            )

        # Check that all logs were created
        bulk_logs = AuditLog.objects.filter(
            user=self.user, action="bulk_update", resource_type="transaction"
        )
        assert bulk_logs.count() == 10

    def test_sensitive_data_detection_in_requests(self):
        """Test detection of sensitive data in request parameters."""
        sensitive_data = {
            "email": "user@example.com",
            "phone": "555-123-4567",
            "ssn": "123-45-6789",
            "normal_field": "regular data",
        }

        request = self.factory.post("/update-profile/", data=sensitive_data)
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        self.middleware(request)

        # Check if middleware detected sensitive fields
        context = request._pii_audit_context
        assert "sensitive_fields_detected" in context
        assert context["sensitive_fields_detected"] is True

    def test_middleware_logs_api_requests(self):
        """Test middleware logs API requests separately."""
        request = self.factory.get("/api/v1/transactions/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_ACCEPT"] = "application/json"

        self.middleware(request)

        context = request._pii_audit_context
        assert context["is_api_request"] is True

    def test_middleware_respects_do_not_track(self):
        """Test middleware respects DNT header for analytics."""
        request = self.factory.get("/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_DNT"] = "1"

        self.middleware(request)

        context = request._pii_audit_context
        assert context["do_not_track"] is True

    def test_middleware_integration_with_django_middleware_stack(self):
        """Test middleware integration with Django's middleware stack."""
        from django.contrib.auth.middleware import AuthenticationMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        # Simulate middleware stack
        request = self.factory.get("/test/")

        # Add session middleware
        session_middleware = SessionMiddleware(lambda r: HttpResponse())
        session_middleware.process_request(request)
        request.session.save()

        # Add auth middleware
        auth_middleware = AuthenticationMiddleware(lambda r: HttpResponse())
        auth_middleware.process_request(request)
        request.user = self.user

        # Add our audit middleware
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        self.middleware(request)

        # Should work with other middleware
        assert hasattr(request, "_pii_audit_context")
        assert hasattr(request, "session")
        assert request.user == self.user

    @patch("apps.core.middleware.logger")
    def test_middleware_error_logging(self, mock_logger):
        """Test that middleware logs errors appropriately."""
        request = self.factory.get("/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Set up the middleware context first
        self.middleware(request)

        # Mock AuditLog.objects.log_action to raise an exception
        with patch(
            "apps.core.models.AuditLog.objects.log_action",
            side_effect=Exception("DB Error"),
        ):
            # This should log an error but not raise
            audit_log = self.middleware.log_user_action(
                request=request, action="test", resource_type="test", resource_id="1"
            )

            # Error should be logged
            assert mock_logger.error.called
            # Should return a mock object instead of failing
            assert audit_log.action == "test"

    def test_get_client_ip_method(self):
        """Test the get_client_ip helper method."""
        # Test X-Forwarded-For with multiple IPs
        request = self.factory.get("/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 198.51.100.1, 192.168.1.1"

        ip = self.middleware.get_client_ip(request)
        assert ip == "203.0.113.1"

        # Test X-Real-IP
        request = self.factory.get("/test/")
        request.META["HTTP_X_REAL_IP"] = "203.0.113.5"

        ip = self.middleware.get_client_ip(request)
        assert ip == "203.0.113.5"

        # Test REMOTE_ADDR fallback
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        ip = self.middleware.get_client_ip(request)
        assert ip == "192.168.1.1"

        # Test no IP available
        request = self.factory.get("/test/")
        # Remove REMOTE_ADDR if it was set by RequestFactory
        if "REMOTE_ADDR" in request.META:
            del request.META["REMOTE_ADDR"]

        ip = self.middleware.get_client_ip(request)
        assert ip is None

    def test_is_sensitive_field_method(self):
        """Test the is_sensitive_field helper method."""
        # Test common PII field names
        assert self.middleware.is_sensitive_field("email") is True
        assert self.middleware.is_sensitive_field("phone") is True
        assert self.middleware.is_sensitive_field("ssn") is True
        assert self.middleware.is_sensitive_field("social_security_number") is True
        assert self.middleware.is_sensitive_field("credit_card") is True
        assert self.middleware.is_sensitive_field("password") is True

        # Test non-sensitive fields
        assert self.middleware.is_sensitive_field("name") is False
        assert self.middleware.is_sensitive_field("category") is False
        assert self.middleware.is_sensitive_field("amount") is False

    def test_detect_sensitive_data_in_request(self):
        """Test detection of sensitive data in request."""
        sensitive_data = {
            "user_email": "test@example.com",
            "phone_number": "555-123-4567",
            "category": "groceries",
            "amount": "50.00",
        }

        request = self.factory.post("/test/", data=sensitive_data)

        has_sensitive = self.middleware.detect_sensitive_data_in_request(request)
        assert has_sensitive is True

        # Test request without sensitive data
        normal_data = {
            "category": "groceries",
            "amount": "50.00",
            "description": "Weekly shopping",
        }

        request = self.factory.post("/test/", data=normal_data)

        has_sensitive = self.middleware.detect_sensitive_data_in_request(request)
        assert has_sensitive is False
