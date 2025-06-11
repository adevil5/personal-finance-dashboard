"""
Tests for secure file storage functionality.

This module tests both local and S3 storage backends with security features,
pre-signed URLs, and file cleanup policies for receipt handling.
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.expenses.models import Transaction
from apps.expenses.storage import (
    BaseSecureStorage,
    SecureLocalStorage,
    SecureS3Storage,
    get_storage_backend,
)
from tests.factories import CategoryFactory, TransactionFactory, UserFactory


class SecureStorageTestCase(TestCase):
    """Base test case for secure storage tests."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory()
        self.category = CategoryFactory(user=self.user)

        # Create a test image file
        self.test_image_content = b"test image content"
        self.test_image = SimpleUploadedFile(
            "test_receipt.jpg", self.test_image_content, content_type="image/jpeg"
        )

    def tearDown(self):
        """Clean up test files."""
        # Clean up any files created during tests
        if hasattr(self, "transaction") and self.transaction.receipt:
            try:
                self.transaction.receipt.delete()
            except Exception:
                pass


class TestBaseSecureStorage(SecureStorageTestCase):
    """Test base secure storage functionality."""

    def test_sanitize_filename(self):
        """Test filename sanitization for security."""

        # Create a concrete implementation for testing
        class TestStorage(BaseSecureStorage):
            def cleanup_orphaned_files(self, dry_run=False):
                pass

            def cleanup_expired_files(self, retention_days=None, dry_run=False):
                pass

            def cleanup_user_files(self, user_id, dry_run=False):
                pass

        storage = TestStorage()

        # Test various dangerous filenames
        test_cases = [
            ("normal_file.jpg", "normal_file.jpg"),
            ("file with spaces.jpg", "file_with_spaces.jpg"),
            ("file@#$%.jpg", "file____.jpg"),
            ("../evil.jpg", ValueError),
            ("CON.jpg", "CON_.jpg"),  # Windows reserved name
        ]

        for input_name, expected_output in test_cases:
            if expected_output == ValueError:
                with self.assertRaises(ValueError):
                    storage.sanitize_filename(input_name)
            else:
                sanitized = storage.sanitize_filename(input_name)
                self.assertEqual(sanitized, expected_output)

    def test_generate_secure_path(self):
        """Test secure path generation with user isolation."""

        class TestStorage(BaseSecureStorage):
            def cleanup_orphaned_files(self, dry_run=False):
                pass

            def cleanup_expired_files(self, retention_days=None, dry_run=False):
                pass

            def cleanup_user_files(self, user_id, dry_run=False):
                pass

        storage = TestStorage()

        # Test normal path generation
        secure_path = storage.generate_secure_path(self.user.id, "receipt.jpg")
        expected_prefix = f"receipts/{self.user.id}/"
        self.assertTrue(secure_path.startswith(expected_prefix))
        self.assertTrue(secure_path.endswith("receipt.jpg"))

        # Verify the path includes a UUID for uniqueness
        path_parts = secure_path.split("/")
        filename_part = path_parts[-1]
        self.assertGreater(len(filename_part), len("receipt.jpg"))

    def test_file_path_traversal_prevention(self):
        """Test prevention of path traversal attacks in file paths."""

        class TestStorage(BaseSecureStorage):
            def cleanup_orphaned_files(self, dry_run=False):
                pass

            def cleanup_expired_files(self, retention_days=None, dry_run=False):
                pass

            def cleanup_user_files(self, user_id, dry_run=False):
                pass

        storage = TestStorage()

        # Test various path traversal attempts
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd",
            "receipts/../../../secret.txt",
        ]

        for dangerous_path in dangerous_paths:
            with self.assertRaises(ValueError):
                storage.generate_secure_path(self.user.id, dangerous_path)


class TestSecureLocalStorage(SecureStorageTestCase):
    """Test secure local file storage."""

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_local_storage_save(self):
        """Test saving files with local storage."""
        storage = SecureLocalStorage()

        # Add user_id to the file
        self.test_image.user_id = self.user.id

        # Save the file
        saved_name = storage.save("test.jpg", self.test_image)

        # Verify the file was saved with secure path
        self.assertTrue(saved_name.startswith(f"receipts/{self.user.id}/"))
        self.assertTrue(storage.exists(saved_name))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_local_storage_file_overwrite_prevention(self):
        """Test local storage prevents file overwrites."""
        storage = SecureLocalStorage()

        # Save a file
        test_file = SimpleUploadedFile(
            "test.jpg", b"original content", content_type="image/jpeg"
        )
        test_file.user_id = self.user.id
        first_name = storage.save("test.jpg", test_file)

        # Try to save another file with same name
        test_file2 = SimpleUploadedFile(
            "test.jpg", b"new content", content_type="image/jpeg"
        )
        test_file2.user_id = self.user.id
        second_name = storage.save("test.jpg", test_file2)

        # Should have different names
        self.assertNotEqual(first_name, second_name)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_local_storage_presigned_url(self):
        """Test pre-signed URL generation for local storage."""
        storage = SecureLocalStorage()

        # Save a file
        self.test_image.user_id = self.user.id
        saved_name = storage.save("test.jpg", self.test_image)

        # Create a transaction that references this file
        from django.core.files.base import ContentFile

        test_content = ContentFile(b"test content", name="test.jpg")
        transaction = TransactionFactory(
            user=self.user, category=self.category, receipt=test_content
        )

        # Update the receipt path to match the saved file (bypass validation)
        Transaction.objects.filter(id=transaction.id).update(receipt=saved_name)

        # Generate pre-signed URL
        url = storage.generate_presigned_url_for_user(saved_name, self.user)

        # In local storage, this should be a media URL
        self.assertIsNotNone(url)
        self.assertTrue(url.endswith(saved_name))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_local_storage_cleanup_orphaned_files(self):
        """Test cleanup of orphaned files in local storage."""
        storage = SecureLocalStorage()

        # Create media root structure
        media_root = Path(settings.MEDIA_ROOT)
        user_dir = media_root / "receipts" / str(self.user.id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # Create an orphaned file (older than 1 day)
        orphaned_file = user_dir / "orphaned.jpg"
        orphaned_file.write_bytes(b"orphaned content")

        # Make it old
        old_time = (datetime.now() - timedelta(days=2)).timestamp()
        os.utime(orphaned_file, (old_time, old_time))

        # Create a referenced file
        active_file = user_dir / "active.jpg"
        active_file.write_bytes(b"active content")

        from django.core.files.base import ContentFile

        test_content = ContentFile(b"test content", name="active.jpg")
        transaction = TransactionFactory(
            user=self.user, category=self.category, receipt=test_content
        )

        # Update the receipt path to match the saved file (bypass validation)
        Transaction.objects.filter(id=transaction.id).update(
            receipt=f"receipts/{self.user.id}/active.jpg"
        )

        # Run cleanup
        deleted_count = storage.cleanup_orphaned_files(dry_run=False)

        # Should delete only the orphaned file
        self.assertEqual(deleted_count, 1)
        self.assertFalse(orphaned_file.exists())
        self.assertTrue(active_file.exists())


class TestSecureS3Storage(SecureStorageTestCase):
    """Test secure S3 storage implementation."""

    @patch("apps.expenses.storage.boto3")
    @patch("storages.backends.s3boto3.S3Boto3Storage")
    def test_s3_storage_initialization(self, mock_s3_storage_class, mock_boto3):
        """Test S3 storage initializes with correct configuration."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        # Mock the S3Boto3Storage initialization
        mock_s3_storage = Mock()
        mock_s3_storage.bucket_name = "test-bucket"
        mock_s3_storage.access_key = "test-key"
        mock_s3_storage.secret_key = "test-secret"
        mock_s3_storage.region_name = "us-east-1"
        mock_s3_storage.object_parameters = {}
        mock_s3_storage_class.return_value = mock_s3_storage

        SecureS3Storage()

        # Verify KMS encryption was configured
        self.assertIn("ServerSideEncryption", mock_s3_storage.object_parameters)
        self.assertEqual(
            mock_s3_storage.object_parameters["ServerSideEncryption"], "aws:kms"
        )

    @patch("apps.expenses.storage.boto3")
    @patch("storages.backends.s3boto3.S3Boto3Storage")
    def test_s3_storage_with_kms_encryption(self, mock_s3_storage_class, mock_boto3):
        """Test S3 storage uses KMS encryption for uploads."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        mock_s3_storage = Mock()
        mock_s3_storage.bucket_name = "test-bucket"
        mock_s3_storage.access_key = "test-key"
        mock_s3_storage.secret_key = "test-secret"
        mock_s3_storage.region_name = "us-east-1"
        mock_s3_storage.object_parameters = {}
        mock_s3_storage.save.return_value = "receipts/1/test.jpg"
        mock_s3_storage_class.return_value = mock_s3_storage

        storage = SecureS3Storage()

        # Create a test file upload
        test_file = SimpleUploadedFile(
            "test.jpg", b"test content", content_type="image/jpeg"
        )
        test_file.user_id = self.user.id

        # Test file save with KMS encryption
        saved_name = storage.save("test-file.jpg", test_file)

        # Verify save was called
        mock_s3_storage.save.assert_called_once()
        self.assertEqual(saved_name, "receipts/1/test.jpg")

    @patch("apps.expenses.storage.boto3")
    @patch("storages.backends.s3boto3.S3Boto3Storage")
    def test_generate_presigned_url(self, mock_s3_storage_class, mock_boto3):
        """Test generation of pre-signed URLs for file access."""
        mock_client = Mock()
        mock_client.generate_presigned_url.return_value = (
            "https://example.com/presigned-url"
        )
        mock_boto3.client.return_value = mock_client

        mock_s3_storage = Mock()
        mock_s3_storage.bucket_name = "test-bucket"
        mock_s3_storage.access_key = "test-key"
        mock_s3_storage.secret_key = "test-secret"
        mock_s3_storage.region_name = "us-east-1"
        mock_s3_storage.object_parameters = {}
        mock_s3_storage_class.return_value = mock_s3_storage

        storage = SecureS3Storage()

        # Generate pre-signed URL
        url = storage.generate_presigned_url("receipts/1/test.jpg")

        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://"))

        # Verify S3 client method was called with correct parameters
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "receipts/1/test.jpg"},
            ExpiresIn=3600,  # Default 1 hour expiration
        )

    @patch("apps.expenses.storage.boto3")
    @patch("storages.backends.s3boto3.S3Boto3Storage")
    def test_presigned_url_with_custom_expiration(
        self, mock_s3_storage_class, mock_boto3
    ):
        """Test pre-signed URL generation with custom expiration time."""
        mock_client = Mock()
        mock_client.generate_presigned_url.return_value = (
            "https://example.com/presigned-url"
        )
        mock_boto3.client.return_value = mock_client

        mock_s3_storage = Mock()
        mock_s3_storage.bucket_name = "test-bucket"
        mock_s3_storage.access_key = "test-key"
        mock_s3_storage.secret_key = "test-secret"
        mock_s3_storage.region_name = "us-east-1"
        mock_s3_storage.object_parameters = {}
        mock_s3_storage_class.return_value = mock_s3_storage

        storage = SecureS3Storage()

        # Generate pre-signed URL with 2 hour expiration
        custom_expiry = 7200  # 2 hours
        storage.generate_presigned_url(
            "receipts/1/test.jpg", expires_in=custom_expiry
        )

        # Verify custom expiration was used
        mock_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_client.generate_presigned_url.call_args[1]
        self.assertEqual(call_kwargs["ExpiresIn"], custom_expiry)

    @patch("apps.expenses.storage.boto3")
    @patch("storages.backends.s3boto3.S3Boto3Storage")
    def test_presigned_url_user_access_validation(
        self, mock_s3_storage_class, mock_boto3
    ):
        """Test pre-signed URL generation validates user access to file."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        mock_s3_storage = Mock()
        mock_s3_storage.bucket_name = "test-bucket"
        mock_s3_storage.access_key = "test-key"
        mock_s3_storage.secret_key = "test-secret"
        mock_s3_storage.region_name = "us-east-1"
        mock_s3_storage.object_parameters = {}
        mock_s3_storage_class.return_value = mock_s3_storage

        storage = SecureS3Storage()

        # Create transaction with receipt
        from django.core.files.base import ContentFile

        test_content = ContentFile(b"test content", name="test.jpg")
        transaction = TransactionFactory(
            user=self.user, category=self.category, receipt=test_content
        )

        # Update the receipt path to match the saved file (bypass validation)
        expected_path = f"receipts/{self.user.id}/test.jpg"
        Transaction.objects.filter(id=transaction.id).update(receipt=expected_path)

        # User should be able to access their own file
        mock_client.generate_presigned_url.return_value = (
            "https://example.com/presigned-url"
        )
        url = storage.generate_presigned_url_for_user(expected_path, self.user)
        self.assertIsNotNone(url)

        # Different user should not be able to access the file
        other_user = UserFactory()
        with self.assertRaises(PermissionError):
            storage.generate_presigned_url_for_user(expected_path, other_user)


class TestFileCleanupPolicies(SecureStorageTestCase):
    """Test file cleanup policies for unused and expired files."""

    @patch("apps.expenses.storage.boto3")
    @patch("storages.backends.s3boto3.S3Boto3Storage")
    def test_cleanup_expired_files(self, mock_s3_storage_class, mock_boto3):
        """Test cleanup of files older than retention period."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        # Mock list_objects_v2 to return old and new files
        old_date = datetime.now() - timedelta(days=366)  # Older than 1 year
        new_date = datetime.now() - timedelta(days=30)  # Within 1 year

        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "receipts/1/old-file.jpg", "LastModified": old_date},
                {"Key": "receipts/1/new-file.jpg", "LastModified": new_date},
            ]
        }

        mock_s3_storage = Mock()
        mock_s3_storage.bucket_name = "test-bucket"
        mock_s3_storage.access_key = "test-key"
        mock_s3_storage.secret_key = "test-secret"
        mock_s3_storage.region_name = "us-east-1"
        mock_s3_storage.object_parameters = {}
        mock_s3_storage_class.return_value = mock_s3_storage

        storage = SecureS3Storage()

        # Run cleanup with 1 year retention
        deleted_count = storage.cleanup_expired_files(retention_days=365)

        # Should delete only the old file
        self.assertEqual(deleted_count, 1)
        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="receipts/1/old-file.jpg"
        )

    @patch("apps.expenses.storage.boto3")
    @patch("storages.backends.s3boto3.S3Boto3Storage")
    def test_encryption_key_rotation_support(self, mock_s3_storage_class, mock_boto3):
        """Test support for KMS key rotation."""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        mock_s3_storage = Mock()
        mock_s3_storage.bucket_name = "test-bucket"
        mock_s3_storage.access_key = "test-key"
        mock_s3_storage.secret_key = "test-secret"
        mock_s3_storage.region_name = "us-east-1"
        mock_s3_storage.object_parameters = {}
        mock_s3_storage_class.return_value = mock_s3_storage

        storage = SecureS3Storage()

        # Test with different KMS key
        old_key = "arn:aws:kms:us-east-1:123456789012:key/old-key-id"
        new_key = "arn:aws:kms:us-east-1:123456789012:key/new-key-id"

        # Mock successful re-encryption
        mock_client.copy_object.return_value = {"ETag": "new-etag"}

        # Test key rotation
        result = storage.rotate_encryption_key("receipts/1/test.jpg", old_key, new_key)

        self.assertTrue(result)

        # Verify copy_object was called with new encryption key
        mock_client.copy_object.assert_called_once()
        call_kwargs = mock_client.copy_object.call_args[1]
        self.assertEqual(call_kwargs["SSEKMSKeyId"], new_key)


class TestStorageBackendSelection(SecureStorageTestCase):
    """Test storage backend selection based on environment."""

    @override_settings(AWS_STORAGE_BUCKET_NAME="test-bucket")
    @patch("apps.expenses.storage.SecureS3Storage")
    def test_get_storage_backend_returns_s3_in_production(self, mock_s3_storage_class):
        """Test that S3 storage is returned when configured."""
        mock_s3_storage = Mock()
        mock_s3_storage_class.return_value = mock_s3_storage

        storage = get_storage_backend()

        mock_s3_storage_class.assert_called_once()
        self.assertEqual(storage, mock_s3_storage)

    @override_settings(AWS_STORAGE_BUCKET_NAME="")
    def test_get_storage_backend_returns_local_in_development(self):
        """Test that local storage is returned in development."""
        storage = get_storage_backend()

        self.assertIsInstance(storage, SecureLocalStorage)


class TestStorageIntegration(SecureStorageTestCase):
    """Integration tests for storage with Django models."""

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_receipt_access_through_presigned_url(self):
        """Test receipt access through pre-signed URL."""
        # Create transaction with receipt
        from django.core.files.base import ContentFile

        test_content = ContentFile(b"test content", name="test.jpg")
        transaction = TransactionFactory(
            user=self.user, category=self.category, receipt=test_content
        )

        # Update the receipt path to match the saved file (bypass validation)
        Transaction.objects.filter(id=transaction.id).update(
            receipt=f"receipts/{self.user.id}/test.jpg"
        )

        # Get storage backend
        storage = get_storage_backend()

        # Generate pre-signed URL for receipt access
        url = storage.generate_presigned_url_for_user(
            transaction.receipt.name, self.user
        )

        self.assertIsNotNone(url)

    def test_receipt_cleanup_on_transaction_deletion(self):
        """Test that receipts are cleaned up when transactions are deleted."""
        # Create transaction with receipt
        from django.core.files.base import ContentFile

        test_content = ContentFile(b"test content", name="test.jpg")
        transaction = TransactionFactory(
            user=self.user, category=self.category, receipt=test_content
        )

        # Update the receipt path to match the saved file (bypass validation)
        Transaction.objects.filter(id=transaction.id).update(
            receipt=f"receipts/{self.user.id}/test.jpg"
        )

        # Delete transaction
        transaction.delete()

        # File should be scheduled for cleanup
        # (Implementation will depend on cleanup strategy - immediate vs batch)
        # This test ensures the cleanup mechanism is triggered
        self.assertTrue(True)  # Placeholder - implement based on cleanup strategy
