"""
Utility functions for expense management.

Provides helper functions for file handling, URL generation, and other
common operations.
"""

import logging
from datetime import datetime
from typing import Optional

from django.http import Http404

from apps.expenses.models import Transaction
from apps.expenses.storage import get_storage_backend

logger = logging.getLogger(__name__)


def generate_secure_file_url(
    file_path: str, user, expires_in: int = 3600
) -> Optional[str]:
    """
    Generate a secure pre-signed URL for file access with user validation.

    Args:
        file_path (str): Path to the file in storage
        user (User): User requesting access
        expires_in (int): URL expiration time in seconds (default: 1 hour)

    Returns:
        str: Pre-signed URL or None if access denied

    Raises:
        PermissionError: If user doesn't have access to the file
    """
    try:
        # Get appropriate storage backend
        storage = get_storage_backend()

        # Generate pre-signed URL with user validation
        url = storage.generate_presigned_url_for_user(file_path, user, expires_in)

        logger.info(f"Generated secure URL for user {user.id}, file: {file_path}")
        return url

    except PermissionError:
        logger.warning(f"Access denied for user {user.id} to file: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Failed to generate secure URL for {file_path}: {e}")
        return None


def get_user_receipt_url(
    transaction_id: int, user, expires_in: int = 3600
) -> Optional[str]:
    """
    Get a secure URL for accessing a transaction receipt.

    Args:
        transaction_id (int): ID of the transaction
        user (User): User requesting access
        expires_in (int): URL expiration time in seconds

    Returns:
        str: Pre-signed URL or None if not found/no access

    Raises:
        Http404: If transaction doesn't exist or user doesn't have access
    """
    try:
        # Get the transaction with user validation
        transaction = Transaction.objects.get(
            id=transaction_id, user=user, is_active=True
        )

        # Check if transaction has a receipt
        if not transaction.receipt:
            return None

        # Generate secure URL for the receipt
        return generate_secure_file_url(transaction.receipt.name, user, expires_in)

    except Transaction.DoesNotExist:
        raise Http404("Transaction not found")


def validate_file_ownership(file_path: str, user) -> bool:
    """
    Validate that a user owns/has access to a specific file.

    Args:
        file_path (str): Path to the file in storage
        user (User): User to validate access for

    Returns:
        bool: True if user has access to the file
    """
    try:
        # Check if file path starts with user's directory
        expected_prefix = f"receipts/{user.id}/"
        if not file_path.startswith(expected_prefix):
            return False

        # Verify the file is referenced by user's active transactions
        return Transaction.objects.filter(
            user=user, receipt__icontains=file_path, is_active=True
        ).exists()

    except Exception as e:
        logger.error(f"Error validating file ownership for {file_path}: {e}")
        return False


def get_file_metadata(file_path: str, user) -> Optional[dict]:
    """
    Get metadata for a file that the user owns.

    Args:
        file_path (str): Path to the file in storage
        user (User): User requesting metadata

    Returns:
        dict: File metadata or None if not accessible
    """
    try:
        # Validate user has access to the file
        if not validate_file_ownership(file_path, user):
            return None

        # Get appropriate storage backend
        storage = get_storage_backend()

        # Get file information (only available for S3)
        if hasattr(storage, "get_file_info"):
            file_info = storage.get_file_info(file_path)

            if file_info:
                logger.info(f"Retrieved metadata for user {user.id}, file: {file_path}")

            return file_info
        else:
            # For local storage, return basic info
            from pathlib import Path

            media_path = Path(storage.location) / file_path
            if media_path.exists():
                stat = media_path.stat()
                return {
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime),
                    "content_type": None,  # Not available for local files
                    "encryption": None,
                    "kms_key_id": None,
                    "etag": None,
                }
            return None

    except Exception as e:
        logger.error(f"Failed to get file metadata for {file_path}: {e}")
        return None


def cleanup_transaction_receipt(transaction):
    """
    Clean up receipt file when a transaction is deleted.

    Args:
        transaction (Transaction): Transaction being deleted
    """
    try:
        if not transaction.receipt:
            return

        file_path = transaction.receipt.name

        # Check if any other active transactions reference this file
        other_references = (
            Transaction.objects.filter(receipt=transaction.receipt, is_active=True)
            .exclude(id=transaction.id)
            .exists()
        )

        # Only delete if no other references exist
        if not other_references:
            # Get appropriate storage backend
            storage = get_storage_backend()

            # Delete the file
            try:
                storage.delete(file_path)
                logger.info(f"Deleted receipt file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete receipt file {file_path}: {e}")
        else:
            logger.info(
                f"Receipt file {file_path} still referenced by other transactions"
            )

    except Exception as e:
        logger.error(
            f"Error during receipt cleanup for transaction {transaction.id}: {e}"
        )


def get_user_storage_usage(user) -> dict:
    """
    Get storage usage statistics for a user.

    Args:
        user (User): User to get statistics for

    Returns:
        dict: Storage usage statistics
    """
    try:
        # Get appropriate storage backend
        storage = get_storage_backend()

        stats = {
            "total_files": 0,
            "total_size": 0,
            "oldest_file": None,
            "newest_file": None,
            "file_types": {},
        }

        # Handle S3 storage
        if hasattr(storage, "s3_client"):
            user_prefix = f"receipts/{user.id}/"
            continuation_token = None

            while True:
                list_params = {
                    "Bucket": storage.bucket_name,
                    "Prefix": user_prefix,
                    "MaxKeys": 1000,
                }

                if continuation_token:
                    list_params["ContinuationToken"] = continuation_token

                response = storage.s3_client.list_objects_v2(**list_params)

                if "Contents" not in response:
                    break

                for obj in response["Contents"]:
                    stats["total_files"] += 1
                    stats["total_size"] += obj["Size"]

                    # Track oldest and newest files
                    file_date = obj["LastModified"]
                    if not stats["oldest_file"] or file_date < stats["oldest_file"]:
                        stats["oldest_file"] = file_date
                    if not stats["newest_file"] or file_date > stats["newest_file"]:
                        stats["newest_file"] = file_date

                    # Track file types
                    file_ext = obj["Key"].split(".")[-1].lower()
                    stats["file_types"][file_ext] = (
                        stats["file_types"].get(file_ext, 0) + 1
                    )

                # Check if there are more objects
                if not response.get("IsTruncated"):
                    break

                continuation_token = response.get("NextContinuationToken")
        else:
            # Handle local storage
            from pathlib import Path

            media_root = Path(storage.location)
            user_dir = media_root / "receipts" / str(user.id)

            if user_dir.exists():
                for file_path in user_dir.iterdir():
                    if file_path.is_file():
                        stats["total_files"] += 1
                        stat = file_path.stat()
                        stats["total_size"] += stat.st_size

                        # Track oldest and newest files
                        file_date = datetime.fromtimestamp(stat.st_mtime)
                        if not stats["oldest_file"] or file_date < stats["oldest_file"]:
                            stats["oldest_file"] = file_date
                        if not stats["newest_file"] or file_date > stats["newest_file"]:
                            stats["newest_file"] = file_date

                        # Track file types
                        file_ext = (
                            file_path.suffix[1:].lower()
                            if file_path.suffix
                            else "unknown"
                        )
                        stats["file_types"][file_ext] = (
                            stats["file_types"].get(file_ext, 0) + 1
                        )

        logger.info(f"Retrieved storage usage for user {user.id}: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Failed to get storage usage for user {user.id}: {e}")
        return {
            "total_files": 0,
            "total_size": 0,
            "oldest_file": None,
            "newest_file": None,
            "file_types": {},
            "error": str(e),
        }
