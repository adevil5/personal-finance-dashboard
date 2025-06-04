"""
Custom Django field types that provide transparent encryption/decryption of PII data.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.db import models

from .encryption import PIIFieldEncryption, get_default_encryption


class BaseEncryptedField:
    """
    Base mixin for encrypted field functionality.
    """

    def __init__(self, *args, encryption_key: Optional[bytes] = None, **kwargs):
        """
        Initialize encrypted field.

        Args:
            encryption_key: Optional custom encryption key for this field
            **kwargs: Standard Django field arguments
        """
        super().__init__(*args, **kwargs)
        self.encryption_key = encryption_key
        self._encryption_instance = None

    def _get_encryption(self) -> PIIFieldEncryption:
        """Get encryption instance for this field."""
        if self._encryption_instance is None:
            if self.encryption_key:
                self._encryption_instance = PIIFieldEncryption(self.encryption_key)
            else:
                self._encryption_instance = get_default_encryption()
        return self._encryption_instance

    def _encrypt_value(self, value: Any) -> Optional[str]:
        """Encrypt a value for database storage."""
        if value is None:
            return None
        return self._get_encryption().encrypt(str(value))

    def _decrypt_value(self, encrypted_value: Optional[str]) -> Optional[str]:
        """Decrypt a value from database storage."""
        if encrypted_value is None:
            return None
        return self._get_encryption().decrypt(encrypted_value)

    def get_prep_value(self, value: Any) -> Optional[str]:
        """Prepare value for database storage by encrypting it."""
        if value is None:
            return None
        return self._encrypt_value(value)

    def from_db_value(self, value: Any, expression, connection) -> Any:
        """Convert value from database to Python."""
        if value is None:
            return None
        return self.to_python(self._decrypt_value(value))

    def value_from_object(self, obj) -> Any:
        """Get the value of this field from a model instance."""
        encrypted_value = getattr(obj, self.attname)
        if encrypted_value is None:
            return None
        return self.to_python(self._decrypt_value(encrypted_value))


class EncryptedCharField(BaseEncryptedField, models.CharField):
    """
    A CharField that encrypts its contents before storing in the database.
    """

    description = "A CharField with automatic PII encryption"

    def __init__(self, *args, **kwargs):
        # Increase max_length to accommodate encrypted data
        if "max_length" in kwargs:
            # Encrypted data is typically 2-3x larger than original
            kwargs["max_length"] = max(kwargs["max_length"] * 3, 255)
        super().__init__(*args, **kwargs)

    def to_python(self, value: Any) -> Optional[str]:
        """Convert value to Python string."""
        if value is None:
            return None
        if isinstance(value, str):
            # If it's already decrypted (e.g., from form input), return as-is
            # If it's encrypted from DB, it will be handled by from_db_value
            return value
        return str(value)

    def validate(self, value: Any, model_instance) -> None:
        """Validate the decrypted value."""
        # Decrypt if needed, then validate length
        if value is not None:
            decrypted_value = value
            if hasattr(self, "_is_encrypted_value") and self._is_encrypted_value(value):
                decrypted_value = self._decrypt_value(value)

            # Check length of decrypted value against original max_length
            original_max_length = getattr(
                self, "_original_max_length", self.max_length // 3
            )
            if len(str(decrypted_value)) > original_max_length:
                raise ValidationError(
                    f"Ensure this value has at most {original_max_length} characters"
                )
        super(models.CharField, self).validate(value, model_instance)

    def _is_encrypted_value(self, value: str) -> bool:
        """Check if a value appears to be encrypted (basic heuristic)."""
        try:
            # Try to decrypt - if it works, it was encrypted
            self._decrypt_value(value)
            return True
        except (ValueError, Exception):
            return False


class EncryptedTextField(BaseEncryptedField, models.TextField):
    """
    A TextField that encrypts its contents before storing in the database.
    """

    description = "A TextField with automatic PII encryption"

    def to_python(self, value: Any) -> Optional[str]:
        """Convert value to Python string."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)


class EncryptedDecimalField(BaseEncryptedField, models.CharField):
    """
    A field that stores Decimal values in encrypted form.
    Uses CharField as base to store encrypted string representation.
    """

    description = "A DecimalField with automatic PII encryption"

    def __init__(self, max_digits: int = 10, decimal_places: int = 2, *args, **kwargs):
        """
        Initialize encrypted decimal field.

        Args:
            max_digits: Maximum number of digits
            decimal_places: Number of decimal places
        """
        self.max_digits = max_digits
        self.decimal_places = decimal_places

        # Calculate max_length for CharField to store encrypted decimal
        # Format: sign + digits + decimal point = max_digits + 2
        decimal_length = max_digits + 2
        # Encrypted data is typically 2-3x larger
        kwargs["max_length"] = decimal_length * 3

        super().__init__(*args, **kwargs)

    def to_python(self, value: Any) -> Optional[Decimal]:
        """Convert value to Python Decimal."""
        if value is None:
            return None

        if isinstance(value, Decimal):
            return value

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            try:
                return Decimal(value)
            except (InvalidOperation, ValueError):
                raise ValidationError(f"Invalid decimal value: {value}")

        raise ValidationError(f"Cannot convert {type(value)} to Decimal")

    def get_prep_value(self, value: Any) -> Optional[str]:
        """Prepare Decimal value for database storage."""
        if value is None:
            return None

        if isinstance(value, Decimal):
            decimal_str = str(value)
        else:
            # Convert to Decimal first to validate
            decimal_value = self.to_python(value)
            decimal_str = str(decimal_value)

        return self._encrypt_value(decimal_str)

    def validate(self, value: Any, model_instance) -> None:
        """Validate decimal value."""
        if value is None:
            return

        decimal_value = self.to_python(value)

        # Check max_digits
        if decimal_value is not None:
            digit_tuple = decimal_value.as_tuple().digits
            if len(digit_tuple) > self.max_digits:
                raise ValidationError(
                    f"Ensure that there are no more than "
                    f"{self.max_digits} digits in total"
                )

            # Check decimal_places
            decimal_places = abs(decimal_value.as_tuple().exponent)
            if decimal_places > self.decimal_places:
                raise ValidationError(
                    f"Ensure that there are no more than "
                    f"{self.decimal_places} decimal places"
                )

    def formfield(self, **kwargs):
        """Return appropriate form field."""
        from django.forms import DecimalField

        defaults = {
            "max_digits": self.max_digits,
            "decimal_places": self.decimal_places,
        }
        defaults.update(kwargs)
        return DecimalField(**defaults)


class EncryptedEmailField(BaseEncryptedField, models.CharField):
    """
    An EmailField that encrypts email addresses before storing in the database.
    """

    description = "An EmailField with automatic PII encryption"

    def __init__(self, *args, **kwargs):
        # Set reasonable max_length for emails (encrypted)
        kwargs.setdefault("max_length", 750)  # 250 chars * 3 for encryption
        super().__init__(*args, **kwargs)

    def to_python(self, value: Any) -> Optional[str]:
        """Convert value to Python string."""
        if value is None:
            return None
        return str(value).strip().lower()

    def validate(self, value: Any, model_instance) -> None:
        """Validate email format."""
        if value is None:
            return

        # Basic email validation
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, value):
            raise ValidationError("Enter a valid email address")

        super().validate(value, model_instance)


class EncryptedPhoneField(BaseEncryptedField, models.CharField):
    """
    A field for storing encrypted phone numbers.
    """

    description = "A phone number field with automatic PII encryption"

    def __init__(self, *args, **kwargs):
        # Set reasonable max_length for phone numbers (encrypted)
        kwargs.setdefault("max_length", 150)  # 50 chars * 3 for encryption
        super().__init__(*args, **kwargs)

    def to_python(self, value: Any) -> Optional[str]:
        """Convert value to Python string, normalizing phone format."""
        if value is None:
            return None

        # Remove all non-digit characters for storage
        import re

        phone_str = re.sub(r"[^\d+]", "", str(value))
        return phone_str if phone_str else None

    def validate(self, value: Any, model_instance) -> None:
        """Validate phone number format."""
        if value is None:
            return

        normalized = self.to_python(value)
        if normalized and len(normalized) < 10:
            raise ValidationError("Phone number must be at least 10 digits")

        super().validate(value, model_instance)
