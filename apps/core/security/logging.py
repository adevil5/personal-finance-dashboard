"""
PII-safe logging utilities to prevent sensitive data from appearing in logs.
"""

import json
import logging
from typing import Any, Dict, Optional

from django.conf import settings

from .pii_detection import PIIDetector


class PIISafeFormatter(logging.Formatter):
    """
    Logging formatter that automatically removes PII from log messages.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the PII-safe formatter."""
        super().__init__(*args, **kwargs)
        self.detector = PIIDetector()
        self.replacement_text = getattr(
            settings, "PII_LOG_REPLACEMENT", "[PII_REDACTED]"
        )

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record while removing PII.

        Args:
            record: Log record to format

        Returns:
            Formatted log message with PII removed
        """
        # Get the original formatted message
        original_message = super().format(record)

        # Remove PII from the message
        safe_message = self.detector.sanitize_for_logging(
            original_message, self.replacement_text
        )

        return safe_message

    def formatException(self, ei) -> str:
        """
        Format exception information while removing PII.

        Args:
            ei: Exception info tuple

        Returns:
            Formatted exception with PII removed
        """
        # Get original exception formatting
        original_exception = super().formatException(ei)

        # Remove PII from exception text
        safe_exception = self.detector.sanitize_for_logging(
            original_exception, self.replacement_text
        )

        return safe_exception


class PIISafeJSONFormatter(logging.Formatter):
    """
    JSON logging formatter that removes PII from structured log data.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the PII-safe JSON formatter."""
        super().__init__(*args, **kwargs)
        self.detector = PIIDetector()
        self.replacement_text = getattr(
            settings, "PII_LOG_REPLACEMENT", "[PII_REDACTED]"
        )

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON while removing PII.

        Args:
            record: Log record to format

        Returns:
            JSON formatted log message with PII removed
        """
        # Create base log data
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith("_"):
                log_data[key] = value

        # Sanitize all string values in the log data
        sanitized_data = self._sanitize_dict(log_data)

        return json.dumps(sanitized_data, default=str, ensure_ascii=False)

    def formatException(self, ei) -> str:
        """
        Format exception information while removing PII.

        Args:
            ei: Exception info tuple

        Returns:
            Formatted exception with PII removed
        """
        # Get original exception formatting
        original_exception = super().formatException(ei)

        # Remove PII from exception text
        safe_exception = self.detector.sanitize_for_logging(
            original_exception, self.replacement_text
        )

        return safe_exception

    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary values to remove PII.

        Args:
            data: Dictionary to sanitize

        Returns:
            Dictionary with PII removed from values
        """
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.detector.sanitize_for_logging(
                    value, self.replacement_text
                )
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = self._sanitize_sequence(value)
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_sequence(self, data) -> list:
        """
        Sanitize sequence (list/tuple) values to remove PII.

        Args:
            data: Sequence to sanitize

        Returns:
            List with PII removed from values
        """
        sanitized = []

        for item in data:
            if isinstance(item, str):
                sanitized.append(
                    self.detector.sanitize_for_logging(item, self.replacement_text)
                )
            elif isinstance(item, dict):
                sanitized.append(self._sanitize_dict(item))
            elif isinstance(item, (list, tuple)):
                sanitized.append(self._sanitize_sequence(item))
            else:
                sanitized.append(item)

        return sanitized


class PIISafeFilter(logging.Filter):
    """
    Logging filter that prevents PII from being logged.
    """

    def __init__(self, name: str = ""):
        """Initialize the PII-safe filter."""
        super().__init__(name)
        self.detector = PIIDetector()

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log records to prevent PII from being logged.

        Args:
            record: Log record to filter

        Returns:
            True if record should be logged, False if it contains PII
        """
        # Check if the message contains PII
        message = record.getMessage()

        if self.detector.has_pii(message):
            # Optionally log a warning about PII detection
            if getattr(settings, "LOG_PII_DETECTION_WARNINGS", False):
                safe_logger = logging.getLogger("pii_detection")
                safe_logger.warning(
                    "PII detected in log message from %s:%s - message blocked",
                    record.module,
                    record.lineno,
                )
            return False

        return True


class AuditLogger:
    """
    Specialized logger for audit events related to PII access.
    """

    def __init__(self, logger_name: str = "pii_audit"):
        """
        Initialize audit logger.

        Args:
            logger_name: Name of the logger to use
        """
        self.logger = logging.getLogger(logger_name)

    def log_pii_access(
        self,
        user_id: Optional[int],
        pii_type: str,
        action: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log PII access events for audit purposes.

        Args:
            user_id: ID of user accessing PII
            pii_type: Type of PII being accessed (email, phone, ssn, etc.)
            action: Action being performed (view, edit, delete, etc.)
            resource_id: ID of the resource containing PII
            ip_address: IP address of the request
            user_agent: User agent string
            additional_context: Additional context data
        """
        audit_data = {
            "event_type": "pii_access",
            "user_id": user_id,
            "pii_type": pii_type,
            "action": action,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "context": additional_context or {},
        }

        self.logger.info("PII access event", extra=audit_data)

    def log_pii_encryption_event(
        self,
        action: str,
        field_name: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log PII encryption/decryption events.

        Args:
            action: Action performed (encrypt, decrypt, key_rotation)
            field_name: Name of the field being processed
            success: Whether the operation was successful
            error_message: Error message if operation failed
        """
        audit_data = {
            "event_type": "pii_encryption",
            "action": action,
            "field_name": field_name,
            "success": success,
            "error_message": error_message,
        }

        level = logging.INFO if success else logging.ERROR
        message = f"PII encryption {action} {'succeeded' if success else 'failed'}"

        self.logger.log(level, message, extra=audit_data)

    def log_data_export(
        self,
        user_id: int,
        export_type: str,
        record_count: int,
        includes_pii: bool,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Log data export events that may contain PII.

        Args:
            user_id: ID of user performing export
            export_type: Type of export (csv, pdf, etc.)
            record_count: Number of records exported
            includes_pii: Whether export includes PII data
            ip_address: IP address of the request
        """
        audit_data = {
            "event_type": "data_export",
            "user_id": user_id,
            "export_type": export_type,
            "record_count": record_count,
            "includes_pii": includes_pii,
            "ip_address": ip_address,
        }

        self.logger.info("Data export event", extra=audit_data)


def configure_pii_safe_logging():
    """
    Configure Django logging to use PII-safe formatters.

    This function should be called during Django setup to ensure
    all logging is PII-safe by default.
    """
    # Get the root logger
    root_logger = logging.getLogger()

    # Add PII filter to all existing handlers
    pii_filter = PIISafeFilter()

    for handler in root_logger.handlers:
        # Replace formatter with PII-safe version
        if isinstance(handler.formatter, logging.Formatter):
            handler.setFormatter(PIISafeFormatter())

        # Add PII filter
        handler.addFilter(pii_filter)

    # Configure specific loggers
    django_logger = logging.getLogger("django")
    pii_filter_django = PIISafeFilter()
    django_logger.addFilter(pii_filter_django)

    # Create audit logger with JSON formatting
    audit_logger = logging.getLogger("pii_audit")
    if not audit_logger.handlers:
        audit_handler = logging.StreamHandler()
        audit_handler.setFormatter(PIISafeJSONFormatter())
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)


def get_safe_logger(name: str) -> logging.Logger:
    """
    Get a logger configured with PII-safe formatting.

    Args:
        name: Logger name

    Returns:
        Logger instance with PII-safe configuration
    """
    logger = logging.getLogger(name)

    # Ensure the logger has PII-safe configuration
    if not any(isinstance(f, PIISafeFilter) for f in logger.filters):
        logger.addFilter(PIISafeFilter())

    return logger
