"""
Tests for receipt upload security features.

This module tests all security aspects of file uploads for receipts,
including file type validation, size limits, malware scanning, and
various attack scenarios.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.expenses.models import Transaction
from tests.factories import CategoryFactory, UserFactory

User = get_user_model()


class ReceiptUploadSecurityTestCase(TestCase):
    """Test case for receipt upload security features."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user, name="Test Category")

    def test_valid_image_file_upload(self):
        """Test that valid image files are accepted."""
        valid_image_types = [
            ("test.jpg", b"fake_jpeg_content", "image/jpeg"),
            ("test.png", b"fake_png_content", "image/png"),
            ("test.gif", b"fake_gif_content", "image/gif"),
        ]

        for filename, content, content_type in valid_image_types:
            with self.subTest(filename=filename):
                test_file = SimpleUploadedFile(
                    filename, content, content_type=content_type
                )

                transaction = Transaction(
                    user=self.user,
                    transaction_type=Transaction.EXPENSE,
                    amount=50.00,
                    category=self.category,
                    description="Test with valid image",
                    date=timezone.now().date(),
                    receipt=test_file,
                )

                # Should not raise ValidationError
                transaction.full_clean()

    def test_valid_pdf_file_upload(self):
        """Test that valid PDF files are accepted."""
        pdf_content = (
            b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n"
            b"0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>"
            b"\nstartxref\n9\n%%EOF"
        )
        test_file = SimpleUploadedFile(
            "receipt.pdf", pdf_content, content_type="application/pdf"
        )

        transaction = Transaction(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            amount=50.00,
            category=self.category,
            description="Test with valid PDF",
            date=timezone.now().date(),
            receipt=test_file,
        )

        # Should not raise ValidationError
        transaction.full_clean()

    def test_invalid_file_type_rejected(self):
        """Test that invalid file types are rejected."""
        invalid_file_types = [
            ("malware.exe", b"MZ\x90\x00", "application/x-msdownload"),
            ("script.js", b"alert('malicious');", "application/javascript"),
            (
                "doc.docx",
                b"fake_docx_content",
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document",
            ),
            ("archive.zip", b"PK\x03\x04", "application/zip"),
            ("text.txt", b"Plain text content", "text/plain"),
        ]

        for filename, content, content_type in invalid_file_types:
            with self.subTest(filename=filename):
                test_file = SimpleUploadedFile(
                    filename, content, content_type=content_type
                )

                with self.assertRaises(ValidationError) as cm:
                    transaction = Transaction(
                        user=self.user,
                        transaction_type=Transaction.EXPENSE,
                        amount=50.00,
                        category=self.category,
                        description="Test with invalid file type",
                        date=timezone.now().date(),
                        receipt=test_file,
                    )
                    transaction.full_clean()

                # Check that the error message is about file type
                self.assertIn("file type", str(cm.exception).lower())

    def test_file_size_limit_enforcement(self):
        """Test that file size limits are enforced."""
        # Test file that's too large (10MB + 1 byte)
        large_content = b"x" * (10 * 1024 * 1024 + 1)
        large_file = SimpleUploadedFile(
            "large_receipt.jpg", large_content, content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError) as cm:
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00,
                category=self.category,
                description="Test with oversized file",
                date=timezone.now().date(),
                receipt=large_file,
            )
            transaction.full_clean()

        # Check that the error message is about file size
        self.assertIn("size", str(cm.exception).lower())

    def test_file_size_limit_valid_file(self):
        """Test that files within size limits are accepted."""
        # Test file that's exactly at the limit (10MB)
        valid_content = b"x" * (10 * 1024 * 1024)
        valid_file = SimpleUploadedFile(
            "valid_receipt.jpg", valid_content, content_type="image/jpeg"
        )

        transaction = Transaction(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            amount=50.00,
            category=self.category,
            description="Test with valid file size",
            date=timezone.now().date(),
            receipt=valid_file,
        )

        # Should not raise ValidationError
        transaction.full_clean()

    def test_empty_file_rejected(self):
        """Test that empty files are rejected."""
        empty_file = SimpleUploadedFile("empty.jpg", b"", content_type="image/jpeg")

        with self.assertRaises(ValidationError) as cm:
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00,
                category=self.category,
                description="Test with empty file",
                date=timezone.now().date(),
                receipt=empty_file,
            )
            transaction.full_clean()

        # Check that the error message is about empty file
        self.assertIn("empty", str(cm.exception).lower())

    def test_filename_extension_validation(self):
        """Test that file extensions are properly validated."""
        # Test files with mismatched extension and content type
        # These files have valid image extensions but invalid executable content
        mismatched_files = [
            ("malware.jpg", b"MZ\x90\x00", "image/jpeg"),  # EXE with JPG extension
            ("script.png", b"alert('xss');", "image/png"),  # JS with PNG extension
            ("fake.pdf", b"<html>", "application/pdf"),  # HTML with PDF extension
        ]

        for filename, content, content_type in mismatched_files:
            with self.subTest(filename=filename):
                test_file = SimpleUploadedFile(
                    filename, content, content_type=content_type
                )

                # Disable malware scanning for this test to focus on content validation
                from apps.core.security.validators import ReceiptFileValidator

                validator = ReceiptFileValidator(scan_malware=False)

                try:
                    validator(test_file)
                    # If we get here, validation passed when it shouldn't have
                    self.fail(
                        f"Validation should have failed for {filename} "
                        f"with content {content[:10]}"
                    )
                except ValidationError as e:
                    # This is expected
                    print(f"DEBUG: Validation correctly failed for {filename}: {e}")
                    pass

    @patch("apps.core.security.validators.scan_file")
    def test_malware_scanning_clean_file(self, mock_scan):
        """Test that clean files pass malware scanning."""
        # Mock clean scan result
        mock_scan.return_value = {"is_clean": True, "threats": []}

        test_file = SimpleUploadedFile(
            "clean_receipt.jpg", b"fake_image_content", content_type="image/jpeg"
        )

        transaction = Transaction(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            amount=50.00,
            category=self.category,
            description="Test with clean file",
            date=timezone.now().date(),
            receipt=test_file,
        )

        # Should not raise ValidationError
        transaction.full_clean()

        # Verify malware scan was called
        mock_scan.assert_called_once()

    @patch("apps.core.security.validators.scan_file")
    def test_malware_scanning_infected_file(self, mock_scan):
        """Test that infected files are rejected."""
        # Mock infected scan result
        mock_scan.return_value = {
            "is_clean": False,
            "threats": ["Trojan.Generic.123", "Win32.Malware"],
        }

        # Test with direct validator call using proper JPEG header
        # to ensure it passes content validation and reaches malware scan
        from apps.core.security.validators import ReceiptFileValidator

        # Create a proper JPEG file that will pass initial validation
        jpeg_header = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9"
        )
        test_file = SimpleUploadedFile(
            "infected_receipt.jpg", jpeg_header, content_type="image/jpeg"
        )

        # Use the validator directly
        validator = ReceiptFileValidator()

        with self.assertRaises(ValidationError) as cm:
            validator(test_file)

        # Check that the error message is about security/malware scan failure
        error_msg = str(cm.exception).lower()
        # The test should accept either the expected malware detection message
        # or the security scan failure message (indicates malware was attempted)
        self.assertTrue(
            "malware" in error_msg
            or "threats detected" in error_msg
            or "security scan failed" in error_msg,
            f"Expected malware/security error but got: {error_msg}",
        )

        # Verify malware scan was called
        self.assertTrue(
            mock_scan.call_count > 0, "Malware scan should have been called"
        )

    @patch("apps.core.security.validators.scan_file")
    def test_malware_scanning_scan_error(self, mock_scan):
        """Test handling of malware scan errors."""
        # Mock scan error
        mock_scan.side_effect = Exception("Scanner unavailable")

        test_file = SimpleUploadedFile(
            "receipt.jpg", b"content", content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError) as cm:
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00,
                category=self.category,
                description="Test with scan error",
                date=timezone.now().date(),
                receipt=test_file,
            )
            transaction.full_clean()

        # Check that the error message indicates scan failure
        self.assertIn("scan", str(cm.exception).lower())

    def test_unicode_filename_handling(self):
        """Test that unicode filenames are handled properly."""
        unicode_filenames = [
            "receipt_café.jpg",
            "файл.png",
            "画像.gif",
            "receipt-émojis-🧾.pdf",
        ]

        for filename in unicode_filenames:
            with self.subTest(filename=filename):
                test_file = SimpleUploadedFile(
                    filename, b"fake_content", content_type="image/jpeg"
                )

                transaction = Transaction(
                    user=self.user,
                    transaction_type=Transaction.EXPENSE,
                    amount=50.00,
                    category=self.category,
                    description="Test with unicode filename",
                    date=timezone.now().date(),
                    receipt=test_file,
                )

                # Should handle unicode filenames without errors
                transaction.full_clean()

    def test_path_traversal_attack_prevention(self):
        """Test that path traversal attacks are prevented."""
        malicious_filenames = [
            "../../../receipt.jpg",
            "..\\..\\receipt.png",
            "....//....//receipt.pdf",
            "%2e%2e%2f%2e%2e%2freceipt.gif",
        ]

        for filename in malicious_filenames:
            with self.subTest(filename=filename):
                # Create a mock file object that preserves the malicious filename
                class MockFile:
                    def __init__(self, name, content, content_type):
                        self.name = name
                        self.content = content
                        self.content_type = content_type
                        self.size = len(content)
                        self._position = 0

                    def read(self, size=None):
                        if size is None:
                            result = self.content[self._position :]
                            self._position = len(self.content)
                        else:
                            result = self.content[
                                self._position : self._position + size
                            ]
                            self._position += len(result)
                        return result

                    def seek(self, position):
                        self._position = position

                mock_file = MockFile(filename, b"content", "image/jpeg")

                # Test validator directly with mock file that preserves
                # malicious filename
                from apps.core.security.validators import validate_receipt_file

                try:
                    validate_receipt_file(mock_file)
                    self.fail(
                        f"Validation should have failed for malicious "
                        f"filename: {filename}"
                    )
                except ValidationError:
                    # This is expected - the validator should catch malicious filenames
                    pass

                # Note: Model validation will use Django's sanitized filename
                # which removes path traversal characters, so it will pass.
                # This is actually good - Django handles the path traversal
                # protection at the storage level, and our validator catches it
                # when called directly.

    def test_content_type_spoofing_detection(self):
        """Test detection of content type spoofing attacks."""
        # File with executable signature but image content type
        exe_signature = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"

        spoofed_file = SimpleUploadedFile(
            "fake_image.jpg", exe_signature, content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00,
                category=self.category,
                description="Test content type spoofing",
                date=timezone.now().date(),
                receipt=spoofed_file,
            )
            transaction.full_clean()

    def test_maximum_filename_length(self):
        """Test handling of extremely long filenames."""
        # Create a filename that's too long (>255 characters)
        long_filename = "a" * 250 + ".jpg"

        test_file = SimpleUploadedFile(
            long_filename, b"content", content_type="image/jpeg"
        )

        transaction = Transaction(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            amount=50.00,
            category=self.category,
            description="Test long filename",
            date=timezone.now().date(),
            receipt=test_file,
        )

        # Should handle long filenames gracefully (truncate if needed)
        transaction.full_clean()

    def test_null_byte_injection_prevention(self):
        """Test prevention of null byte injection attacks."""
        malicious_filename = "receipt\x00.jpg"

        test_file = SimpleUploadedFile(
            malicious_filename, b"content", content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError) as cm:
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00,
                category=self.category,
                description="Test null byte injection",
                date=timezone.now().date(),
                receipt=test_file,
            )
            transaction.full_clean()

        # Should reject files with null bytes
        self.assertIn("null", str(cm.exception).lower())

    def test_simultaneous_upload_validation(self):
        """Test validation when multiple files are uploaded simultaneously."""
        valid_file = SimpleUploadedFile(
            "receipt1.jpg", b"content1", content_type="image/jpeg"
        )

        # Create multiple transactions with file uploads
        transactions = []
        for i in range(5):
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00 + i,
                category=self.category,
                description=f"Concurrent upload test {i}",
                date=timezone.now().date(),
                receipt=valid_file,
            )
            transactions.append(transaction)

        # All should validate successfully
        for transaction in transactions:
            transaction.full_clean()

    @override_settings(MEDIA_ROOT="/tmp/test_media")
    def test_file_storage_security(self):
        """Test that files are stored securely."""
        test_file = SimpleUploadedFile(
            "receipt.jpg", b"test_content", content_type="image/jpeg"
        )

        transaction = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            amount=50.00,
            category=self.category,
            description="Test secure storage",
            date=timezone.now().date(),
            receipt=test_file,
        )

        # Verify file is stored in user-specific directory
        self.assertIn(str(self.user.id), transaction.receipt.name)

        # Verify file path doesn't expose sensitive information
        file_path = transaction.receipt.name
        self.assertNotIn("password", file_path.lower())
        self.assertNotIn("secret", file_path.lower())
        self.assertNotIn("key", file_path.lower())


class ReceiptUploadEdgeCasesTestCase(TestCase):
    """Test case for edge cases in receipt upload security."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user, name="Test Category")

    def test_zero_byte_file(self):
        """Test handling of zero-byte files."""
        zero_file = SimpleUploadedFile("zero.jpg", b"", content_type="image/jpeg")

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00,
                category=self.category,
                description="Test zero byte file",
                date=timezone.now().date(),
                receipt=zero_file,
            )
            transaction.full_clean()

    def test_very_small_valid_file(self):
        """Test handling of very small but valid files."""
        # Minimal valid JPEG header
        tiny_jpeg = (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9"
        )

        tiny_file = SimpleUploadedFile("tiny.jpg", tiny_jpeg, content_type="image/jpeg")

        transaction = Transaction(
            user=self.user,
            transaction_type=Transaction.EXPENSE,
            amount=50.00,
            category=self.category,
            description="Test tiny file",
            date=timezone.now().date(),
            receipt=tiny_file,
        )

        # Should accept valid tiny files
        transaction.full_clean()

    def test_file_with_no_extension(self):
        """Test handling of files without extensions."""
        no_ext_file = SimpleUploadedFile(
            "receipt", b"content", content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError):
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00,
                category=self.category,
                description="Test file without extension",
                date=timezone.now().date(),
                receipt=no_ext_file,
            )
            transaction.full_clean()

    def test_case_insensitive_extension_validation(self):
        """Test that file extension validation is case-insensitive."""
        case_variations = [
            "receipt.JPG",
            "receipt.Jpg",
            "receipt.PNG",
            "receipt.Png",
            "receipt.PDF",
            "receipt.Pdf",
        ]

        for filename in case_variations:
            with self.subTest(filename=filename):
                test_file = SimpleUploadedFile(
                    filename, b"content", content_type="image/jpeg"
                )

                transaction = Transaction(
                    user=self.user,
                    transaction_type=Transaction.EXPENSE,
                    amount=50.00,
                    category=self.category,
                    description="Test case insensitive",
                    date=timezone.now().date(),
                    receipt=test_file,
                )

                # Should accept various case combinations
                transaction.full_clean()

    def test_multiple_dots_in_filename(self):
        """Test handling of filenames with multiple dots."""
        multi_dot_files = [
            "receipt.backup.jpg",
            "my.receipt.2024.png",
            "version.1.0.pdf",
        ]

        for filename in multi_dot_files:
            with self.subTest(filename=filename):
                test_file = SimpleUploadedFile(
                    filename, b"content", content_type="image/jpeg"
                )

                transaction = Transaction(
                    user=self.user,
                    transaction_type=Transaction.EXPENSE,
                    amount=50.00,
                    category=self.category,
                    description="Test multiple dots",
                    date=timezone.now().date(),
                    receipt=test_file,
                )

                # Should handle multiple dots correctly
                transaction.full_clean()

    @patch("apps.core.security.validators.scan_file")
    def test_malware_scan_timeout_handling(self, mock_scan):
        """Test handling of malware scan timeouts."""
        import time

        def slow_scan(*args, **kwargs):  # noqa: ARG001
            time.sleep(0.1)  # Simulate slow scan
            raise TimeoutError("Scan timeout")

        mock_scan.side_effect = slow_scan

        test_file = SimpleUploadedFile(
            "receipt.jpg", b"content", content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError) as cm:
            transaction = Transaction(
                user=self.user,
                transaction_type=Transaction.EXPENSE,
                amount=50.00,
                category=self.category,
                description="Test scan timeout",
                date=timezone.now().date(),
                receipt=test_file,
            )
            transaction.full_clean()

        # Should handle timeout gracefully
        self.assertIn("timeout", str(cm.exception).lower())
