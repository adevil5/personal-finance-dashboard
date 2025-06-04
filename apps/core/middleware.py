"""
Audit middleware for tracking user actions and PII access.
"""

import logging
import re
from typing import TYPE_CHECKING, Optional

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

if TYPE_CHECKING:
    from .models import AuditLog, PIIAccessLog

logger = logging.getLogger(__name__)


class PIIAuditMiddleware(MiddlewareMixin):
    """
    Middleware to track user actions and PII access for audit compliance.

    This middleware:
    - Sets up audit context for each request
    - Provides convenient methods for logging user actions and PII access
    - Extracts client IP addresses from various headers
    - Detects sensitive data in request parameters
    """

    # Common field names that might contain PII
    SENSITIVE_FIELD_PATTERNS = [
        r".*email.*",
        r".*phone.*",
        r".*ssn.*",
        r".*social.*security.*",
        r".*credit.*card.*",
        r".*password.*",
        r".*address.*",
        r".*zip.*code.*",
        r".*postal.*code.*",
        r".*birth.*date.*",
        r".*dob.*",
    ]

    def __init__(self, get_response):
        """Initialize the middleware."""
        self.get_response = get_response
        self.sensitive_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SENSITIVE_FIELD_PATTERNS
        ]
        super().__init__(get_response)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process the request and set up audit context."""
        try:
            self.process_request(request)
            response = self.get_response(request)
            return response
        except Exception as e:
            # Log the error but don't break the request
            logger.error(f"Error in PIIAuditMiddleware: {e}", exc_info=True)
            # Re-raise the exception to maintain normal error handling
            raise

    def process_request(self, request: HttpRequest) -> None:
        """
        Set up audit context for the request.

        Args:
            request: Django HTTP request object
        """
        # Extract user information
        user = getattr(request, "user", None)
        if user and getattr(user, "is_anonymous", True):
            user = None

        # Extract client IP address
        ip_address = self.get_client_ip(request)

        # Extract user agent
        user_agent = request.META.get("HTTP_USER_AGENT")

        # Detect if this is an API request
        is_api_request = request.path.startswith("/api/") or request.META.get(
            "HTTP_ACCEPT", ""
        ).startswith("application/json")

        # Check for Do Not Track header
        do_not_track = request.META.get("HTTP_DNT") == "1"

        # Detect sensitive data in request
        sensitive_fields_detected = self.detect_sensitive_data_in_request(request)

        # Set up audit context on the request
        setattr(
            request,
            "_pii_audit_context",
            {
                "user": user,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "request_path": request.path,
                "request_method": request.method,
                "is_api_request": is_api_request,
                "do_not_track": do_not_track,
                "sensitive_fields_detected": sensitive_fields_detected,
            },
        )

    def get_client_ip(self, request: HttpRequest) -> Optional[str]:
        """
        Extract the real client IP address from request headers.

        Args:
            request: Django HTTP request object

        Returns:
            Client IP address or None if not available
        """
        # Check X-Forwarded-For header (for load balancers/proxies)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Take the first IP (original client)
            return x_forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (nginx)
        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip.strip()

        # Fallback to REMOTE_ADDR
        return request.META.get("REMOTE_ADDR")

    def is_sensitive_field(self, field_name: str) -> bool:
        """
        Check if a field name indicates it might contain PII.

        Args:
            field_name: Name of the field to check

        Returns:
            True if field name suggests PII content
        """
        field_name_lower = field_name.lower()
        return any(
            pattern.match(field_name_lower) for pattern in self.sensitive_patterns
        )

    def detect_sensitive_data_in_request(self, request: HttpRequest) -> bool:
        """
        Detect if the request contains fields that might have sensitive data.

        Args:
            request: Django HTTP request object

        Returns:
            True if sensitive fields are detected
        """
        # Check POST data
        if hasattr(request, "POST") and request.POST:
            for field_name in request.POST.keys():
                if self.is_sensitive_field(field_name):
                    return True

        # Check GET parameters
        if hasattr(request, "GET") and request.GET:
            for field_name in request.GET.keys():
                if self.is_sensitive_field(field_name):
                    return True

        return False

    def log_user_action(
        self,
        request: HttpRequest,
        action: str,
        resource_type: str,
        resource_id: str,
        metadata: Optional[dict] = None,
    ) -> "AuditLog":
        """
        Log a user action for audit purposes.

        Args:
            request: Django HTTP request object
            action: Action performed (e.g., 'create', 'update', 'delete', 'view')
            resource_type: Type of resource (e.g., 'transaction', 'budget')
            resource_id: ID of the resource
            metadata: Additional metadata about the action

        Returns:
            Created AuditLog instance
        """
        try:
            from .models import AuditLog

            return AuditLog.objects.log_action(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request=request,
                metadata=metadata or {},
            )
        except Exception as e:
            logger.error(f"Failed to log user action: {e}", exc_info=True)
            # Return a mock object to prevent breaking the request flow
            from .models import AuditLog

            return AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
            )

    def log_pii_access(
        self,
        request: HttpRequest,
        pii_type: str,
        action: str,
        field_name: str,
        model_name: str,
        record_id: str,
        accessed_value: Optional[str] = None,
        access_reason: Optional[str] = None,
    ) -> "PIIAccessLog":
        """
        Log PII access for audit purposes.

        Args:
            request: Django HTTP request object
            pii_type: Type of PII (e.g., 'email', 'phone', 'ssn')
            action: Action performed (e.g., 'view', 'update', 'delete')
            field_name: Name of the field containing PII
            model_name: Name of the model containing PII
            record_id: ID of the record containing PII
            accessed_value: The actual PII value accessed (will be hashed)
            access_reason: Reason for accessing the PII

        Returns:
            Created PIIAccessLog instance
        """
        try:
            from .models import PIIAccessLog

            return PIIAccessLog.objects.log_pii_access(
                pii_type=pii_type,
                action=action,
                field_name=field_name,
                model_name=model_name,
                record_id=record_id,
                request=request,
                accessed_value=accessed_value,
                access_reason=access_reason,
            )
        except Exception as e:
            logger.error(f"Failed to log PII access: {e}", exc_info=True)
            # Return a mock object to prevent breaking the request flow
            from .models import PIIAccessLog

            return PIIAccessLog(
                pii_type=pii_type,
                action=action,
                field_name=field_name,
                model_name=model_name,
                record_id=record_id,
            )

    def log_api_access(
        self,
        request: HttpRequest,
        endpoint: str,
        response_status: int,
        response_size: Optional[int] = None,
    ) -> "AuditLog":
        """
        Log API access for audit purposes.

        Args:
            request: Django HTTP request object
            endpoint: API endpoint accessed
            response_status: HTTP response status code
            response_size: Size of response in bytes

        Returns:
            Created AuditLog instance
        """
        metadata = {
            "endpoint": endpoint,
            "response_status": response_status,
            "request_method": request.method,
        }

        if response_size is not None:
            metadata["response_size"] = response_size

        return self.log_user_action(
            request=request,
            action="api_access",
            resource_type="api_endpoint",
            resource_id=endpoint,
            metadata=metadata,
        )

    def log_bulk_action(
        self,
        request: HttpRequest,
        action: str,
        resource_type: str,
        resource_ids: list,
        metadata: Optional[dict] = None,
    ) -> list:
        """
        Log bulk actions efficiently.

        Args:
            request: Django HTTP request object
            action: Action performed
            resource_type: Type of resources
            resource_ids: List of resource IDs
            metadata: Additional metadata

        Returns:
            List of created AuditLog instances
        """
        logs = []
        bulk_metadata = metadata or {}
        bulk_metadata.update(
            {
                "bulk_operation": True,
                "total_records": len(resource_ids),
            }
        )

        for resource_id in resource_ids:
            log = self.log_user_action(
                request=request,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=bulk_metadata.copy(),
            )
            logs.append(log)

        return logs

    def get_audit_context(self, request: HttpRequest) -> dict:
        """
        Get the audit context for the current request.

        Args:
            request: Django HTTP request object

        Returns:
            Audit context dictionary
        """
        return getattr(request, "_pii_audit_context", {})

    def should_audit_request(self, request: HttpRequest) -> bool:
        """
        Determine if a request should be audited based on various criteria.

        Args:
            request: Django HTTP request object

        Returns:
            True if request should be audited
        """
        context = self.get_audit_context(request)

        # Don't audit if user requested DNT
        if context.get("do_not_track", False):
            return False

        # Always audit if sensitive fields detected
        if context.get("sensitive_fields_detected", False):
            return True

        # Always audit API requests
        if context.get("is_api_request", False):
            return True

        # Don't audit static file requests
        if request.path.startswith("/static/") or request.path.startswith("/media/"):
            return False

        # Audit authenticated user requests
        return context.get("user") is not None
