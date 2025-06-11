"""
Secure file storage implementation for receipts and documents.

This module provides secure storage backends for both development (local)
and production (S3 with KMS encryption), with pre-signed URL generation
and file cleanup policies.
"""

import logging
import os
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

from apps.core.security.validators import validate_receipt_file

logger = logging.getLogger(__name__)

# Optional boto3 import for S3 storage
try:
    import boto3
except ImportError:
    boto3 = None


class BaseSecureStorage(ABC):
    """
    Abstract base class for secure file storage.

    Provides common security features for both local and S3 storage:
    - File validation and sanitization
    - User access control
    - Cleanup policies
    - Audit logging
    """

    def __init__(self):
        """Initialize base secure storage."""
        self.retention_days = getattr(settings, "FILE_RETENTION_DAYS", 365)
        self.cleanup_batch_size = getattr(settings, "CLEANUP_BATCH_SIZE", 1000)

    def sanitize_filename(self, filename):
        """
        Sanitize filename to prevent security issues.

        Args:
            filename (str): Original filename

        Returns:
            str: Sanitized filename

        Raises:
            ValueError: If filename contains path traversal attempts
        """
        # Check for path traversal attempts
        if ".." in filename or filename.startswith("/"):
            raise ValueError("Invalid filename: path traversal not allowed")

        # Extract just the filename part (remove any path)
        filename = os.path.basename(filename)

        # Replace dangerous characters
        filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

        # Handle Windows reserved names
        windows_reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        name_part = filename.split(".")[0].upper()
        if name_part in windows_reserved:
            filename = name_part + "_" + filename[len(name_part) :]

        return filename

    def generate_secure_path(self, user_id, filename):
        """
        Generate a secure file path with user isolation and uniqueness.

        Args:
            user_id (int): User ID for path isolation
            filename (str): Original filename

        Returns:
            str: Secure file path

        Raises:
            ValueError: If filename contains dangerous elements
        """
        # Validate inputs
        if not user_id or not filename:
            raise ValueError("User ID and filename are required")

        # Sanitize filename first
        clean_filename = self.sanitize_filename(filename)

        # Generate unique identifier to prevent conflicts
        unique_id = uuid.uuid4().hex[:8]

        # Create filename with unique prefix
        name_part, ext_part = os.path.splitext(clean_filename)
        secure_filename = f"{unique_id}_{name_part}{ext_part}"

        # Build secure path: receipts/{user_id}/{unique_filename}
        secure_path = f"receipts/{user_id}/{secure_filename}"

        return secure_path

    def validate_and_save(self, name, content, max_length=None):
        """
        Validate file content before saving.

        Args:
            name (str): File name
            content (File): File content
            max_length (int): Maximum filename length

        Raises:
            ValueError: If file fails validation
        """
        # Validate file content using existing validators
        try:
            validate_receipt_file(content)
        except ValidationError as e:
            logger.warning(f"File upload rejected: {e}")
            raise ValueError(f"File validation failed: {e}")

        # Log the upload attempt
        logger.info(
            f"File upload started: {name}, "
            f"size: {getattr(content, 'size', 'unknown')}, "
            f"content_type: {getattr(content, 'content_type', 'unknown')}"
        )

    def _user_has_file_access(self, file_key, user):
        """
        Check if user has access to the specified file.

        Args:
            file_key (str): File path/key
            user (User): User to check access for

        Returns:
            bool: True if user has access
        """
        # Check if file path starts with user's directory
        expected_prefix = f"receipts/{user.id}/"
        if not file_key.startswith(expected_prefix):
            return False

        # Additional check: verify the file is referenced by user's transactions
        from apps.expenses.models import Transaction

        return Transaction.objects.filter(
            user=user, receipt__icontains=file_key, is_active=True
        ).exists()

    @abstractmethod
    def cleanup_orphaned_files(self, dry_run=False):
        """Clean up orphaned files not referenced by any transaction."""
        pass

    @abstractmethod
    def cleanup_expired_files(self, retention_days=None, dry_run=False):
        """Clean up files older than retention period."""
        pass

    @abstractmethod
    def cleanup_user_files(self, user_id, dry_run=False):
        """Clean up all files for a specific user."""
        pass


@deconstructible
class SecureLocalStorage(FileSystemStorage, BaseSecureStorage):
    """
    Secure local file storage for development.

    Extends Django's FileSystemStorage with security features:
    - Path traversal prevention
    - User access validation
    - Local cleanup policies
    """

    def __init__(self, **kwargs):
        """Initialize secure local storage."""
        FileSystemStorage.__init__(self, **kwargs)
        BaseSecureStorage.__init__(self)

    def save(self, name, content, max_length=None):
        """
        Save file with security validations.

        Args:
            name (str): File name
            content (File): File content
            max_length (int): Maximum filename length

        Returns:
            str: Saved file name
        """
        # Validate file
        self.validate_and_save(name, content, max_length)

        # Generate secure path
        if hasattr(content, "user_id"):
            secure_name = self.generate_secure_path(content.user_id, name)
        else:
            secure_name = self.sanitize_filename(name)

        try:
            # Save with parent method
            saved_name = super().save(secure_name, content, max_length)
            logger.info(f"File upload successful: {saved_name}")
            return saved_name

        except Exception as e:
            logger.error(f"File upload failed: {secure_name}, error: {e}")
            raise

    def generate_presigned_url(self, file_path, expires_in=3600):
        """
        Generate a URL for file access (local development).

        In development, this returns a direct URL to the media file.

        Args:
            file_path (str): File path
            expires_in (int): Ignored in local storage

        Returns:
            str: URL to access the file
        """
        # In development, just return the media URL
        return self.url(file_path)

    def generate_presigned_url_for_user(self, file_path, user, expires_in=3600):
        """
        Generate URL with user access validation.

        Args:
            file_path (str): File path
            user (User): User requesting access
            expires_in (int): Ignored in local storage

        Returns:
            str: URL to access the file

        Raises:
            PermissionError: If user doesn't have access
        """
        # Validate user has access
        if not self._user_has_file_access(file_path, user):
            logger.warning(f"Access denied for user {user.id} to file {file_path}")
            raise PermissionError("Access denied to this file")

        return self.generate_presigned_url(file_path, expires_in)

    def cleanup_orphaned_files(self, dry_run=False):
        """
        Clean up orphaned files in local storage.

        Args:
            dry_run (bool): If True, only report what would be deleted

        Returns:
            int: Number of files deleted
        """
        from apps.expenses.models import Transaction

        logger.info(f"Starting orphaned files cleanup (dry_run={dry_run})")

        deleted_count = 0
        media_root = Path(settings.MEDIA_ROOT)
        receipts_dir = media_root / "receipts"

        if not receipts_dir.exists():
            return 0

        # Get all referenced files from database
        referenced_files = set(
            Transaction.objects.filter(
                receipt__isnull=False, is_active=True
            ).values_list("receipt", flat=True)
        )

        # Walk through receipts directory
        for user_dir in receipts_dir.iterdir():
            if not user_dir.is_dir():
                continue

            for file_path in user_dir.iterdir():
                if not file_path.is_file():
                    continue

                # Get relative path from media root
                relative_path = str(file_path.relative_to(media_root))

                # Skip if file is referenced
                if any(relative_path in ref_file for ref_file in referenced_files):
                    continue

                # Skip recently uploaded files (grace period)
                file_age = datetime.now() - datetime.fromtimestamp(
                    file_path.stat().st_mtime
                )
                if file_age.days < 1:  # 1 day grace period
                    continue

                if dry_run:
                    logger.info(f"Would delete orphaned file: {relative_path}")
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"Deleted orphaned file: {relative_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete {relative_path}: {e}")
                        continue

                deleted_count += 1

        logger.info(
            f"Orphaned files cleanup completed. Files processed: {deleted_count}"
        )
        return deleted_count

    def cleanup_expired_files(self, retention_days=None, dry_run=False):
        """
        Clean up files older than retention period.

        Args:
            retention_days (int): Days to retain files
            dry_run (bool): If True, only report what would be deleted

        Returns:
            int: Number of files deleted
        """
        if retention_days is None:
            retention_days = self.retention_days

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        logger.info(
            f"Starting expired files cleanup (retention: {retention_days} days, "
            f"cutoff: {cutoff_date}, dry_run={dry_run})"
        )

        deleted_count = 0
        media_root = Path(settings.MEDIA_ROOT)
        receipts_dir = media_root / "receipts"

        if not receipts_dir.exists():
            return 0

        # Walk through receipts directory
        for user_dir in receipts_dir.iterdir():
            if not user_dir.is_dir():
                continue

            for file_path in user_dir.iterdir():
                if not file_path.is_file():
                    continue

                # Check file age
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime > cutoff_date:
                    continue

                relative_path = str(file_path.relative_to(media_root))

                if dry_run:
                    logger.info(
                        f"Would delete expired file: {relative_path} "
                        f"(age: {file_mtime})"
                    )
                else:
                    try:
                        file_path.unlink()
                        logger.info(f"Deleted expired file: {relative_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete {relative_path}: {e}")
                        continue

                deleted_count += 1

        logger.info(
            f"Expired files cleanup completed. Files processed: {deleted_count}"
        )
        return deleted_count

    def cleanup_user_files(self, user_id, dry_run=False):
        """
        Clean up all files for a specific user.

        Args:
            user_id (int): User ID whose files to delete
            dry_run (bool): If True, only report what would be deleted

        Returns:
            int: Number of files deleted
        """
        logger.info(
            f"Starting user files cleanup for user {user_id} (dry_run={dry_run})"
        )

        deleted_count = 0
        media_root = Path(settings.MEDIA_ROOT)
        user_dir = media_root / "receipts" / str(user_id)

        if not user_dir.exists():
            return 0

        # Delete all files in user directory
        for file_path in user_dir.iterdir():
            if not file_path.is_file():
                continue

            relative_path = str(file_path.relative_to(media_root))

            if dry_run:
                logger.info(f"Would delete user file: {relative_path}")
            else:
                try:
                    file_path.unlink()
                    logger.info(f"Deleted user file: {relative_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {relative_path}: {e}")
                    continue

            deleted_count += 1

        # Remove empty user directory
        if not dry_run and deleted_count > 0:
            try:
                user_dir.rmdir()
                logger.info(f"Removed empty directory for user {user_id}")
            except Exception as e:
                logger.debug(f"Could not remove user directory: {e}")

        logger.info(
            f"User files cleanup completed for user {user_id}. "
            f"Files processed: {deleted_count}"
        )
        return deleted_count

    def get_available_name(self, name, max_length=None):
        """
        Get available name, preventing overwrites.

        Args:
            name (str): Desired filename
            max_length (int): Maximum filename length

        Returns:
            str: Available filename
        """
        # If file exists, generate unique name
        if self.exists(name):
            # Split name and extension
            dir_name, file_name = os.path.split(name)
            file_root, file_ext = os.path.splitext(file_name)

            # Generate unique name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{file_root}_{timestamp}{file_ext}"

            if dir_name:
                name = os.path.join(dir_name, unique_name)
            else:
                name = unique_name

        return super().get_available_name(name, max_length)


@deconstructible
class SecureS3Storage(BaseSecureStorage):
    """
    Secure S3 storage backend with KMS encryption.

    Features:
    - KMS encryption for all uploaded files
    - Pre-signed URL generation with user access validation
    - S3-specific cleanup policies
    - Comprehensive audit logging

    Note: Only loaded in production when S3 is configured.
    """

    def __init__(self, **kwargs):
        """Initialize secure S3 storage with KMS encryption."""
        super().__init__()

        # Check imports for S3 functionality
        if boto3 is None:
            raise ImproperlyConfigured(
                "S3 storage requires boto3 and django-storages[s3]. "
                "Install with: pip install boto3 django-storages[s3]"
            )

        try:
            from botocore.exceptions import NoCredentialsError
            from storages.backends.s3boto3 import S3Boto3Storage

            self._boto3 = boto3
            self._NoCredentialsError = NoCredentialsError
            self._S3Boto3Storage = S3Boto3Storage

        except ImportError:
            raise ImproperlyConfigured(
                "S3 storage requires boto3 and django-storages[s3]. "
                "Install with: pip install boto3 django-storages[s3]"
            )

        # Initialize S3 storage parent
        self._storage = self._S3Boto3Storage(**kwargs)

        # Configure KMS encryption
        self._storage.object_parameters.update(
            {
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": getattr(settings, "AWS_S3_KMS_KEY_ID", "alias/aws/s3"),
            }
        )

        # Initialize S3 client for additional operations
        self._s3_client = None

        # Copy necessary attributes
        self.bucket_name = self._storage.bucket_name
        self.access_key = self._storage.access_key
        self.secret_key = self._storage.secret_key
        self.region_name = self._storage.region_name

    @property
    def s3_client(self):
        """Lazy initialization of S3 client."""
        if self._s3_client is None:
            try:
                self._s3_client = self._boto3.client(
                    "s3",
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region_name,
                )
            except self._NoCredentialsError:
                raise ImproperlyConfigured(
                    "AWS credentials not found. Please configure AWS_ACCESS_KEY_ID "
                    "and AWS_SECRET_ACCESS_KEY."
                )
        return self._s3_client

    def save(self, name, content, max_length=None):
        """Save file with KMS encryption and security validations."""
        # Validate file
        self.validate_and_save(name, content, max_length)

        # Generate secure path
        if hasattr(content, "user_id"):
            secure_name = self.generate_secure_path(content.user_id, name)
        else:
            secure_name = self.sanitize_filename(name)

        try:
            # Save with S3 storage (includes KMS encryption)
            saved_name = self._storage.save(secure_name, content, max_length)
            logger.info(f"File upload successful: {saved_name}")
            return saved_name

        except Exception as e:
            logger.error(f"File upload failed: {secure_name}, error: {e}")
            raise

    def delete(self, name):
        """Delete file from S3."""
        return self._storage.delete(name)

    def exists(self, name):
        """Check if file exists in S3."""
        return self._storage.exists(name)

    def url(self, name):
        """Get URL for file (returns S3 URL)."""
        return self._storage.url(name)

    def get_available_name(self, name, max_length=None):
        """Get available name, preventing overwrites."""
        # Check if file exists
        if self._storage.exists(name):
            # Split name and extension
            dir_name, file_name = os.path.split(name)
            file_root, file_ext = os.path.splitext(file_name)

            # Generate unique name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{file_root}_{timestamp}{file_ext}"

            if dir_name:
                name = os.path.join(dir_name, unique_name)
            else:
                name = unique_name

        return self._storage.get_available_name(name, max_length)

    def generate_presigned_url(self, file_key, expires_in=3600):
        """
        Generate a pre-signed URL for secure file access.

        Args:
            file_key (str): S3 object key
            expires_in (int): URL expiration time in seconds (default: 1 hour)

        Returns:
            str: Pre-signed URL
        """
        try:
            from botocore.exceptions import ClientError

            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_key},
                ExpiresIn=expires_in,
            )

            logger.info(
                f"Pre-signed URL generated for: {file_key}, expires in: {expires_in}s"
            )
            return url

        except ClientError as e:
            logger.error(f"Failed to generate pre-signed URL for {file_key}: {e}")
            raise

    def generate_presigned_url_for_user(self, file_key, user, expires_in=3600):
        """Generate pre-signed URL with user access validation."""
        # Validate user has access to this file
        if not self._user_has_file_access(file_key, user):
            logger.warning(f"Access denied for user {user.id} to file {file_key}")
            raise PermissionError("Access denied to this file")

        return self.generate_presigned_url(file_key, expires_in)

    def cleanup_orphaned_files(self, dry_run=False):
        """Clean up files not referenced by any active transaction."""
        from botocore.exceptions import ClientError

        from apps.expenses.models import Transaction

        logger.info(f"Starting orphaned files cleanup (dry_run={dry_run})")

        deleted_count = 0
        continuation_token = None

        try:
            while True:
                # List objects in receipts directory
                list_params = {
                    "Bucket": self.bucket_name,
                    "Prefix": "receipts/",
                    "MaxKeys": self.cleanup_batch_size,
                }

                if continuation_token:
                    list_params["ContinuationToken"] = continuation_token

                response = self.s3_client.list_objects_v2(**list_params)

                if "Contents" not in response:
                    break

                # Get all referenced file paths from database
                referenced_files = set(
                    Transaction.objects.filter(
                        receipt__isnull=False, is_active=True
                    ).values_list("receipt", flat=True)
                )

                # Check each file
                for obj in response["Contents"]:
                    file_key = obj["Key"]

                    # Skip if file is referenced by active transaction
                    if any(file_key in ref_file for ref_file in referenced_files):
                        continue

                    # Skip recently uploaded files (grace period)
                    file_age = (
                        datetime.now(obj["LastModified"].tzinfo) - obj["LastModified"]
                    )
                    if file_age.days < 1:  # 1 day grace period
                        continue

                    if dry_run:
                        logger.info(f"Would delete orphaned file: {file_key}")
                    else:
                        try:
                            self.s3_client.delete_object(
                                Bucket=self.bucket_name, Key=file_key
                            )
                            logger.info(f"Deleted orphaned file: {file_key}")
                        except ClientError as e:
                            logger.error(f"Failed to delete {file_key}: {e}")
                            continue

                    deleted_count += 1

                # Check if there are more objects
                if not response.get("IsTruncated"):
                    break

                continuation_token = response.get("NextContinuationToken")

        except ClientError as e:
            logger.error(f"Error during orphaned files cleanup: {e}")
            raise

        logger.info(
            f"Orphaned files cleanup completed. Files processed: {deleted_count}"
        )
        return deleted_count

    def cleanup_expired_files(self, retention_days=None, dry_run=False):
        """Clean up files older than retention period."""
        from botocore.exceptions import ClientError

        if retention_days is None:
            retention_days = self.retention_days

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        logger.info(
            f"Starting expired files cleanup (retention: {retention_days} days, "
            f"cutoff: {cutoff_date}, dry_run={dry_run})"
        )

        deleted_count = 0
        continuation_token = None

        try:
            while True:
                # List objects in receipts directory
                list_params = {
                    "Bucket": self.bucket_name,
                    "Prefix": "receipts/",
                    "MaxKeys": self.cleanup_batch_size,
                }

                if continuation_token:
                    list_params["ContinuationToken"] = continuation_token

                response = self.s3_client.list_objects_v2(**list_params)

                if "Contents" not in response:
                    break

                # Check each file
                for obj in response["Contents"]:
                    file_key = obj["Key"]
                    file_modified = obj["LastModified"]

                    # Skip if file is not expired
                    if file_modified.replace(tzinfo=None) > cutoff_date:
                        continue

                    if dry_run:
                        logger.info(
                            f"Would delete expired file: {file_key} "
                            f"(age: {file_modified})"
                        )
                    else:
                        try:
                            self.s3_client.delete_object(
                                Bucket=self.bucket_name, Key=file_key
                            )
                            logger.info(f"Deleted expired file: {file_key}")
                        except ClientError as e:
                            logger.error(f"Failed to delete {file_key}: {e}")
                            continue

                    deleted_count += 1

                # Check if there are more objects
                if not response.get("IsTruncated"):
                    break

                continuation_token = response.get("NextContinuationToken")

        except ClientError as e:
            logger.error(f"Error during expired files cleanup: {e}")
            raise

        logger.info(
            f"Expired files cleanup completed. Files processed: {deleted_count}"
        )
        return deleted_count

    def cleanup_user_files(self, user_id, dry_run=False):
        """Clean up all files for a specific user."""
        from botocore.exceptions import ClientError

        user_prefix = f"receipts/{user_id}/"

        logger.info(
            f"Starting user files cleanup for user {user_id} (dry_run={dry_run})"
        )

        deleted_count = 0
        continuation_token = None

        try:
            while True:
                # List objects for specific user
                list_params = {
                    "Bucket": self.bucket_name,
                    "Prefix": user_prefix,
                    "MaxKeys": self.cleanup_batch_size,
                }

                if continuation_token:
                    list_params["ContinuationToken"] = continuation_token

                response = self.s3_client.list_objects_v2(**list_params)

                if "Contents" not in response:
                    break

                # Delete all files for this user
                for obj in response["Contents"]:
                    file_key = obj["Key"]

                    if dry_run:
                        logger.info(f"Would delete user file: {file_key}")
                    else:
                        try:
                            self.s3_client.delete_object(
                                Bucket=self.bucket_name, Key=file_key
                            )
                            logger.info(f"Deleted user file: {file_key}")
                        except ClientError as e:
                            logger.error(f"Failed to delete {file_key}: {e}")
                            continue

                    deleted_count += 1

                # Check if there are more objects
                if not response.get("IsTruncated"):
                    break

                continuation_token = response.get("NextContinuationToken")

        except ClientError as e:
            logger.error(f"Error during user files cleanup: {e}")
            raise

        logger.info(
            f"User files cleanup completed for user {user_id}. "
            f"Files processed: {deleted_count}"
        )
        return deleted_count

    def rotate_encryption_key(self, file_key, old_key_id, new_key_id):
        """Rotate KMS encryption key for an existing file."""
        from botocore.exceptions import ClientError

        try:
            # Copy object with new encryption key
            copy_source = {"Bucket": self.bucket_name, "Key": file_key}

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=file_key,
                ServerSideEncryption="aws:kms",
                SSEKMSKeyId=new_key_id,
                MetadataDirective="COPY",
            )

            logger.info(
                f"Encryption key rotated for {file_key}: {old_key_id} -> {new_key_id}"
            )
            return True

        except ClientError as e:
            logger.error(f"Failed to rotate encryption key for {file_key}: {e}")
            return False

    def get_file_info(self, file_key):
        """Get metadata information for a file."""
        from botocore.exceptions import ClientError

        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)

            return {
                "size": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "content_type": response.get("ContentType"),
                "encryption": response.get("ServerSideEncryption"),
                "kms_key_id": response.get("SSEKMSKeyId"),
                "etag": response.get("ETag"),
            }

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            logger.error(f"Failed to get file info for {file_key}: {e}")
            raise


def get_storage_backend():
    """
    Get appropriate storage backend based on environment.

    Returns:
        Storage backend instance (SecureLocalStorage or SecureS3Storage)
    """
    # Check if we're in production with S3 configured
    if (
        hasattr(settings, "AWS_STORAGE_BUCKET_NAME")
        and settings.AWS_STORAGE_BUCKET_NAME
    ):
        return SecureS3Storage()
    else:
        # Use local storage for development
        return SecureLocalStorage()
