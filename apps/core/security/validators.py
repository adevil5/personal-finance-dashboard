"""
Security validators for file uploads.

This module provides comprehensive validation for uploaded files,
including type checking, size limits, malware scanning, and
protection against various attack vectors.
"""

import logging
import os
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.deconstruct import deconstructible

from .malware import MalwareScanError, is_suspicious_filename, scan_file

logger = logging.getLogger(__name__)


@deconstructible
class ReceiptFileValidator:
    """
    Comprehensive validator for receipt file uploads.

    Validates file type, size, content, and scans for malware.
    """

    # Allowed file types
    ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".pdf"]
    ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/gif", "application/pdf"]

    # File size limits
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MIN_FILE_SIZE = 1  # 1 byte (no empty files)

    # Magic bytes for file type detection
    FILE_SIGNATURES = {
        b"\xFF\xD8\xFF": "image/jpeg",
        b"\x89PNG\r\n\x1A\n": "image/png",
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
        b"%PDF-": "application/pdf",
    }

    def __init__(
        self,
        max_size: Optional[int] = None,
        allowed_extensions: Optional[List[str]] = None,
        scan_malware: bool = True,
    ):
        """
        Initialize validator with custom settings.

        Args:
            max_size: Maximum file size in bytes
            allowed_extensions: List of allowed file extensions
            scan_malware: Whether to perform malware scanning
        """
        self.max_size = max_size or self.MAX_FILE_SIZE
        self.allowed_extensions = allowed_extensions or self.ALLOWED_EXTENSIONS
        self.scan_malware = scan_malware

    def __call__(self, file: UploadedFile) -> None:
        """
        Validate the uploaded file.

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If file fails any validation check
        """
        if not file:
            return

        try:
            self._validate_file_size(file)
            self._validate_file_extension(file)
            self._validate_file_content(file)
            self._validate_filename_security(file)

            if self.scan_malware:
                self._validate_malware_scan(file)
                logger.debug("Malware scan validation passed")

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during file validation: {e}")
            raise ValidationError("File validation failed due to an internal error.")

    def _validate_file_size(self, file: UploadedFile) -> None:
        """Validate file size is within acceptable limits."""
        if file.size < self.MIN_FILE_SIZE:
            raise ValidationError("Empty files are not allowed.")

        if file.size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            raise ValidationError(f"File size exceeds maximum limit of {max_mb:.1f}MB.")

    def _validate_file_extension(self, file: UploadedFile) -> None:
        """Validate file extension is allowed."""
        if not file.name:
            raise ValidationError("File must have a name.")

        # Extract extension
        file_ext = os.path.splitext(file.name.lower())[1]

        if not file_ext:
            raise ValidationError("File must have an extension.")

        if file_ext not in [ext.lower() for ext in self.allowed_extensions]:
            allowed = ", ".join(self.allowed_extensions)
            raise ValidationError(
                f"File type '{file_ext}' not allowed. Allowed types: {allowed}"
            )

    def _validate_file_content(self, file: UploadedFile) -> None:
        """Validate file content matches declared type."""
        # Read beginning of file to check magic bytes
        try:
            file.seek(0)
            header = file.read(64)  # Read first 64 bytes
            file.seek(0)  # Reset file position
        except (AttributeError, IOError):
            # Handle FieldFile objects that might not support seek/read the same way
            if hasattr(file, "file") and hasattr(file.file, "read"):
                file.file.seek(0)
                header = file.file.read(64)
                file.file.seek(0)
            else:
                # If we can't read the file, skip content validation
                return

        if not header:
            raise ValidationError("File appears to be empty or corrupted.")

        # Check if content matches declared content type
        detected_type = self._detect_file_type(header)

        # Check for executable content in any file (always reject)
        if self._contains_executable_content(header):
            raise ValidationError("File content does not match allowed file types.")

        # If we detected a specific type, validate it's allowed
        if detected_type and detected_type not in self.ALLOWED_MIME_TYPES:
            raise ValidationError("File content does not match allowed file types.")

        # Additional validation for specific types
        content_type = getattr(file, "content_type", None)
        if content_type:
            if content_type not in self.ALLOWED_MIME_TYPES:
                raise ValidationError(f"Content type '{content_type}' not allowed.")

            # Check for content type spoofing
            if detected_type and detected_type != content_type:
                # Allow some flexibility for JPEG variants
                if not (
                    detected_type == "image/jpeg"
                    and content_type in ["image/jpeg", "image/jpg"]
                ):
                    raise ValidationError(
                        "File content does not match declared content type."
                    )

    def _detect_file_type(self, header: bytes) -> Optional[str]:
        """Detect file type from magic bytes."""
        for signature, mime_type in self.FILE_SIGNATURES.items():
            if header.startswith(signature):
                return mime_type
        return None

    def _contains_executable_content(self, header: bytes) -> bool:
        """Check if file contains executable content."""
        # Check for common executable signatures
        executable_signatures = [
            b"MZ",  # Windows PE executable (including .exe, .dll)
            b"\x7fELF",  # Linux ELF executable
            b"\xcf\xfa\xed\xfe",  # Mach-O executable (macOS)
            b"\xfe\xed\xfa\xce",  # Mach-O executable (macOS, different endian)
        ]

        for signature in executable_signatures:
            if header.startswith(signature):
                return True

        # Check for script content that shouldn't be in image/PDF files
        header_lower = header.lower()
        script_patterns = [
            b"<script",
            b"javascript:",
            b"vbscript:",
            b"<?php",
            b"<%",
            b"<html>",
            b"alert(",
            b"document.",
            b"window.",
            b"eval(",
        ]

        for pattern in script_patterns:
            if pattern in header_lower:
                return True

        return False

    def _validate_filename_security(self, file: UploadedFile) -> None:
        """Validate filename for security issues."""
        if not file.name:
            return

        filename = file.name

        # Check for suspicious filename patterns
        if is_suspicious_filename(filename):
            raise ValidationError("Filename contains suspicious patterns.")

        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValidationError("Filename contains invalid path characters.")

        # Check for URL-encoded path traversal attempts
        import urllib.parse

        decoded_filename = urllib.parse.unquote(filename)
        if (
            ".." in decoded_filename
            or "/" in decoded_filename
            or "\\" in decoded_filename
        ):
            raise ValidationError("Filename contains invalid path characters.")

        # Check for null bytes
        if "\x00" in filename:
            raise ValidationError("Filename contains null bytes.")

        # Check filename length
        if len(filename) > 255:
            raise ValidationError("Filename is too long (maximum 255 characters).")

        # Check for control characters
        for char in filename:
            if ord(char) < 32 and char not in ["\t", "\n", "\r"]:
                raise ValidationError("Filename contains invalid control characters.")

    def _validate_malware_scan(self, file: UploadedFile) -> None:
        """Perform malware scan on the file."""
        try:
            scan_result = scan_file(file)
            logger.debug(f"Malware scan result: {scan_result}")

            if not scan_result.get("is_clean", True):
                threats = scan_result.get("threats", [])
                threat_list = ", ".join(threats)
                raise ValidationError(
                    f"File failed malware scan. Threats detected: {threat_list}"
                )

        except MalwareScanError as e:
            logger.warning(f"Malware scan failed: {e}")
            # Fail securely - reject file if scan fails
            if "timeout" in str(e).lower():
                raise ValidationError(
                    "File malware scan timeout. Upload rejected for security."
                )
            else:
                raise ValidationError(
                    "File could not be scanned for malware. "
                    "Upload rejected for security."
                )
        except Exception as e:
            logger.error(f"Unexpected error during malware scan: {e}")
            if "timeout" in str(e).lower():
                raise ValidationError(
                    "File malware scan timeout. Upload rejected for security."
                )
            else:
                raise ValidationError("File security scan failed. Upload rejected.")


@deconstructible
class ImageFileValidator(ReceiptFileValidator):
    """Validator specifically for image files."""

    ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif"]
    ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/gif"]


@deconstructible
class PDFFileValidator(ReceiptFileValidator):
    """Validator specifically for PDF files."""

    ALLOWED_EXTENSIONS = [".pdf"]
    ALLOWED_MIME_TYPES = ["application/pdf"]


def validate_receipt_file(file: UploadedFile) -> None:
    """
    Convenience function to validate receipt files.

    Args:
        file: Django UploadedFile instance

    Raises:
        ValidationError: If file fails validation
    """
    validator = ReceiptFileValidator()
    validator(file)


def validate_image_file(file: UploadedFile) -> None:
    """
    Convenience function to validate image files.

    Args:
        file: Django UploadedFile instance

    Raises:
        ValidationError: If file fails validation
    """
    validator = ImageFileValidator()
    validator(file)


def validate_pdf_file(file: UploadedFile) -> None:
    """
    Convenience function to validate PDF files.

    Args:
        file: Django UploadedFile instance

    Raises:
        ValidationError: If file fails validation
    """
    validator = PDFFileValidator()
    validator(file)
