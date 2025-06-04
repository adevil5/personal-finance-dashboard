"""
PII Field Encryption utilities for secure handling of sensitive data.
"""

import base64
import os
from typing import List, Optional, Union

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class PIIFieldEncryption:
    """
    Handles encryption and decryption of PII fields using Fernet symmetric encryption.
    Supports key rotation for enhanced security.
    """

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize encryption handler.

        Args:
            encryption_key: Optional encryption key. If not provided,
                          will use settings.PII_ENCRYPTION_KEY
        """
        self._primary_key = encryption_key or self._get_primary_key()
        self._rotation_keys: List[bytes] = []
        self._fernet = self._create_fernet()

    def _get_primary_key(self) -> bytes:
        """Get primary encryption key from settings or environment."""
        key = getattr(settings, "PII_ENCRYPTION_KEY", None)
        if not key:
            key = os.environ.get("PII_ENCRYPTION_KEY")

        if not key:
            raise ImproperlyConfigured(
                "PII_ENCRYPTION_KEY must be set in settings or environment variables"
            )

        if isinstance(key, str):
            try:
                return base64.urlsafe_b64decode(key.encode())
            except Exception:
                raise ImproperlyConfigured(
                    "PII_ENCRYPTION_KEY must be a valid base64-encoded Fernet key"
                )

        return key

    def _create_fernet(self) -> Union[Fernet, MultiFernet]:
        """Create Fernet instance, supporting multiple keys for rotation."""
        keys = [self._primary_key] + self._rotation_keys

        if len(keys) == 1:
            return Fernet(keys[0])
        else:
            # Use MultiFernet for key rotation support
            return MultiFernet([Fernet(key) for key in keys])

    def encrypt(self, value: Optional[str]) -> Optional[str]:
        """
        Encrypt a string value.

        Args:
            value: The plaintext string to encrypt

        Returns:
            Base64-encoded encrypted string, or None if input is None
        """
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        try:
            encrypted_bytes = self._fernet.encrypt(value.encode("utf-8"))
            return base64.urlsafe_b64encode(encrypted_bytes).decode("ascii")
        except Exception as e:
            raise ValueError(f"Failed to encrypt value: {e}")

    def decrypt(self, encrypted_value: Optional[str]) -> Optional[str]:
        """
        Decrypt an encrypted string value.

        Args:
            encrypted_value: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string, or None if input is None

        Raises:
            ValueError: If decryption fails
        """
        if encrypted_value is None:
            return None

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode("ascii"))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            raise ValueError("Invalid encrypted data - cannot decrypt")
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {e}")

    def rotate_key(self, new_key: bytes) -> None:
        """
        Add a new key for encryption and keep old keys for decryption.

        Args:
            new_key: New Fernet key to use for encryption
        """
        if not isinstance(new_key, bytes):
            raise ValueError("New key must be bytes")

        # Add current primary key to rotation keys
        if self._primary_key not in self._rotation_keys:
            self._rotation_keys.append(self._primary_key)

        # Set new primary key
        self._primary_key = new_key

        # Recreate Fernet with new key configuration
        self._fernet = self._create_fernet()

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new Fernet encryption key.

        Returns:
            New 32-byte Fernet key
        """
        return Fernet.generate_key()

    def re_encrypt_with_new_key(self, encrypted_value: str, new_key: bytes) -> str:
        """
        Re-encrypt data with a new key (useful for key rotation).

        Args:
            encrypted_value: Currently encrypted data
            new_key: New key to encrypt with

        Returns:
            Data encrypted with new key
        """
        # Decrypt with current keys
        plaintext = self.decrypt(encrypted_value)

        # Create new encryption instance with new key
        new_encryption = PIIFieldEncryption(new_key)

        # Encrypt with new key
        return new_encryption.encrypt(plaintext)

    def get_key_info(self) -> dict:
        """
        Get information about current encryption keys (for monitoring/debugging).

        Returns:
            Dictionary with key information (without exposing actual keys)
        """
        return {
            "has_primary_key": self._primary_key is not None,
            "rotation_keys_count": len(self._rotation_keys),
            "supports_key_rotation": len(self._rotation_keys) > 0,
        }


# Global instance for use across the application
_default_encryption = None


def get_default_encryption() -> PIIFieldEncryption:
    """
    Get the default encryption instance.

    Returns:
        Default PIIFieldEncryption instance
    """
    global _default_encryption
    if _default_encryption is None:
        _default_encryption = PIIFieldEncryption()
    return _default_encryption


def encrypt_pii(value: Optional[str]) -> Optional[str]:
    """
    Convenience function to encrypt PII data using default encryption.

    Args:
        value: Plaintext value to encrypt

    Returns:
        Encrypted value
    """
    return get_default_encryption().encrypt(value)


def decrypt_pii(encrypted_value: Optional[str]) -> Optional[str]:
    """
    Convenience function to decrypt PII data using default encryption.

    Args:
        encrypted_value: Encrypted value to decrypt

    Returns:
        Decrypted plaintext value
    """
    return get_default_encryption().decrypt(encrypted_value)
