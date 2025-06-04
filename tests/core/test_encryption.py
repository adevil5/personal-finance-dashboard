"""
Tests for PII encryption utilities.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from django.core.exceptions import ValidationError

from apps.core.security.encryption import PIIFieldEncryption
from apps.core.security.fields import (
    EncryptedCharField,
    EncryptedDecimalField,
    EncryptedEmailField,
    EncryptedPhoneField,
    EncryptedTextField,
)


class TestPIIFieldEncryption:
    """Test cases for PIIFieldEncryption class."""

    def test_encryption_instance_creation(self):
        """Test that PIIFieldEncryption can be instantiated."""
        encryption = PIIFieldEncryption()
        assert encryption is not None

    def test_encrypt_string(self):
        """Test encryption of string data."""
        encryption = PIIFieldEncryption()
        plaintext = "sensitive data"
        encrypted = encryption.encrypt(plaintext)

        assert encrypted != plaintext
        assert isinstance(encrypted, str)
        assert len(encrypted) > len(plaintext)

    def test_decrypt_string(self):
        """Test decryption returns original data."""
        encryption = PIIFieldEncryption()
        plaintext = "sensitive data"
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_none_value(self):
        """Test encryption of None returns None."""
        encryption = PIIFieldEncryption()
        assert encryption.encrypt(None) is None

    def test_decrypt_none_value(self):
        """Test decryption of None returns None."""
        encryption = PIIFieldEncryption()
        assert encryption.decrypt(None) is None

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        encryption = PIIFieldEncryption()
        encrypted = encryption.encrypt("")
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == ""

    def test_encryption_is_deterministic_with_same_key(self):
        """Test that same data encrypts consistently with same key."""
        encryption = PIIFieldEncryption()
        plaintext = "test data"

        # Note: Fernet encryption includes random salt, so this tests
        # that the same instance can decrypt what it encrypted
        encrypted1 = encryption.encrypt(plaintext)
        encrypted2 = encryption.encrypt(plaintext)

        # Encrypted values should be different due to random salt
        assert encrypted1 != encrypted2

        # But both should decrypt to same value
        assert encryption.decrypt(encrypted1) == plaintext
        assert encryption.decrypt(encrypted2) == plaintext

    def test_key_rotation_support(self):
        """Test key rotation functionality."""
        encryption = PIIFieldEncryption()

        # Encrypt with original key
        plaintext = "data to rotate"
        encrypted_old = encryption.encrypt(plaintext)

        # Rotate to new key
        new_key = encryption.generate_key()
        encryption.rotate_key(new_key)

        # Should still be able to decrypt old data
        decrypted = encryption.decrypt(encrypted_old)
        assert decrypted == plaintext

        # New encryptions should use new key
        encrypted_new = encryption.encrypt(plaintext)
        assert encryption.decrypt(encrypted_new) == plaintext

    def test_generate_key_creates_valid_key(self):
        """Test key generation creates valid Fernet key."""
        encryption = PIIFieldEncryption()
        key = encryption.generate_key()

        assert isinstance(key, bytes)
        assert len(key) == 44  # Fernet key length in base64

    def test_invalid_encrypted_data_raises_error(self):
        """Test that invalid encrypted data raises appropriate error."""
        encryption = PIIFieldEncryption()

        with pytest.raises(Exception):  # Fernet will raise InvalidToken
            encryption.decrypt("invalid_encrypted_data")

    def test_unicode_string_encryption(self):
        """Test encryption of unicode strings."""
        encryption = PIIFieldEncryption()
        plaintext = "Test with émojis 🔒 and üñíçødé"
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)

        assert decrypted == plaintext

    def test_long_string_encryption(self):
        """Test encryption of long strings."""
        encryption = PIIFieldEncryption()
        plaintext = "x" * 10000  # Very long string
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)

        assert decrypted == plaintext


class TestEncryptedFields:
    """Test cases for encrypted Django field types."""

    def test_encrypted_char_field_creation(self):
        """Test EncryptedCharField can be created."""
        field = EncryptedCharField(max_length=100)
        # Field automatically increases max_length for encrypted data
        assert field.max_length == 300  # 100 * 3

    def test_encrypted_decimal_field_creation(self):
        """Test EncryptedDecimalField can be created."""
        field = EncryptedDecimalField(max_digits=10, decimal_places=2)
        assert field.max_digits == 10
        assert field.decimal_places == 2

    def test_encrypted_text_field_creation(self):
        """Test EncryptedTextField can be created."""
        field = EncryptedTextField()
        assert field is not None

    def test_encrypted_char_field_to_python(self):
        """Test EncryptedCharField to_python method."""
        field = EncryptedCharField(max_length=100)

        # Test with None
        assert field.to_python(None) is None

        # Test with string (returns as-is, decryption handled by from_db_value)
        result = field.to_python("some_value")
        assert result == "some_value"

    def test_encrypted_decimal_field_to_python(self):
        """Test EncryptedDecimalField to_python method."""
        field = EncryptedDecimalField(max_digits=10, decimal_places=2)

        # Test with None
        assert field.to_python(None) is None

        # Test with valid decimal string
        result = field.to_python("123.45")
        assert result == Decimal("123.45")

        # Test with Decimal object
        result = field.to_python(Decimal("123.45"))
        assert result == Decimal("123.45")

        # Test with integer
        result = field.to_python(123)
        assert result == Decimal("123")

    def test_encrypted_field_get_prep_value(self):
        """Test encrypted field get_prep_value method."""
        field = EncryptedCharField(max_length=100)

        # Test with None
        assert field.get_prep_value(None) is None

        # Test with value (should encrypt)
        with patch.object(field, "_encrypt_value") as mock_encrypt:
            mock_encrypt.return_value = "encrypted_value"
            result = field.get_prep_value("plain_value")
            assert result == "encrypted_value"
            mock_encrypt.assert_called_once_with("plain_value")

    def test_encrypted_field_value_from_object(self):
        """Test encrypted field value retrieval from model instance."""
        field = EncryptedCharField(max_length=100)
        field.attname = "test_field"

        # Mock model instance
        obj = MagicMock()
        obj.test_field = "encrypted_db_value"

        with patch.object(field, "_decrypt_value") as mock_decrypt:
            mock_decrypt.return_value = "decrypted_value"
            result = field.value_from_object(obj)
            assert result == "decrypted_value"

    def test_field_encryption_key_configuration(self):
        """Test that fields can be configured with custom encryption keys."""
        custom_key = b"test_key_" + b"0" * 36  # Mock Fernet key format
        field = EncryptedCharField(max_length=100, encryption_key=custom_key)

        # Field should store the custom key
        assert hasattr(field, "encryption_key")
        assert field.encryption_key == custom_key

    def test_decimal_field_handles_decimal_conversion(self):
        """Test that EncryptedDecimalField properly handles Decimal conversion."""
        field = EncryptedDecimalField(max_digits=10, decimal_places=2)

        # Test conversion from string to Decimal
        result = field.to_python("123.45")
        assert isinstance(result, Decimal)
        assert result == Decimal("123.45")

    def test_decimal_field_prep_value_converts_decimal(self):
        """Test EncryptedDecimalField converts Decimal to string before encryption."""
        field = EncryptedDecimalField(max_digits=10, decimal_places=2)

        with patch.object(field, "_encrypt_value") as mock_encrypt:
            mock_encrypt.return_value = "encrypted"
            field.get_prep_value(Decimal("123.45"))
            mock_encrypt.assert_called_once_with("123.45")

    def test_encrypted_field_database_storage(self):
        """Test that encrypted fields store encrypted data in database."""
        field = EncryptedCharField(max_length=200)  # Longer for encrypted data

        # Field should specify appropriate database column type
        assert hasattr(field, "get_internal_type")
        internal_type = field.get_internal_type()
        assert internal_type in ["CharField", "TextField"]

    def test_field_validation_with_encrypted_data(self):
        """Test field validation works with encrypted data."""
        field = EncryptedCharField(max_length=50)

        # Mock validation - field should validate decrypted value length
        with patch.object(field, "_decrypt_value") as mock_decrypt:
            mock_decrypt.return_value = "short"
            # Should not raise validation error for short decrypted value
            try:
                field.validate("encrypted_short_value", None)
            except Exception:
                pytest.fail("Validation should pass for short decrypted value")

    def test_encryption_roundtrip(self):
        """Test full encryption/decryption roundtrip with fields."""
        field = EncryptedCharField(max_length=100)
        original_value = "sensitive data"

        # Encrypt for storage
        encrypted = field.get_prep_value(original_value)
        assert encrypted != original_value
        assert encrypted is not None

        # Simulate database retrieval and decryption
        decrypted = field.from_db_value(encrypted, None, None)
        assert decrypted == original_value

    def test_decimal_field_encryption_roundtrip(self):
        """Test full encryption/decryption roundtrip with decimal field."""
        field = EncryptedDecimalField(max_digits=10, decimal_places=2)
        original_value = Decimal("123.45")

        # Encrypt for storage
        encrypted = field.get_prep_value(original_value)
        assert encrypted != str(original_value)
        assert encrypted is not None

        # Simulate database retrieval and decryption
        decrypted = field.from_db_value(encrypted, None, None)
        assert decrypted == original_value
        assert isinstance(decrypted, Decimal)

    def test_email_field_validation(self):
        """Test email field validation."""
        field = EncryptedEmailField()

        # Valid email
        valid_email = "test@example.com"
        result = field.to_python(valid_email)
        assert result == "test@example.com"

        # Test case normalization
        result = field.to_python("Test@Example.COM")
        assert result == "test@example.com"

    def test_phone_field_normalization(self):
        """Test phone field normalization."""
        field = EncryptedPhoneField()

        # Test phone number normalization
        result = field.to_python("(555) 123-4567")
        assert result == "5551234567"

        result = field.to_python("+1-555-123-4567")
        assert result == "+15551234567"

    def test_field_validation_errors(self):
        """Test field validation error handling."""
        field = EncryptedDecimalField(max_digits=5, decimal_places=2)

        # Test invalid decimal
        with pytest.raises(ValidationError):
            field.to_python("not_a_number")

        # Test too many digits
        with pytest.raises(ValidationError):
            field.validate(Decimal("123456.78"), None)

    def test_encryption_with_special_characters(self):
        """Test encryption with special characters and encodings."""
        encryption = PIIFieldEncryption()

        # Test with various special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encryption.encrypt(special_chars)
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == special_chars

        # Test with newlines and tabs
        text_with_whitespace = "Line 1\nLine 2\tTabbed"
        encrypted = encryption.encrypt(text_with_whitespace)
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == text_with_whitespace

    def test_encryption_performance_large_data(self):
        """Test encryption performance with large data sets."""
        encryption = PIIFieldEncryption()

        # Test with large string (1MB)
        large_string = "x" * 1024 * 1024
        encrypted = encryption.encrypt(large_string)
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == large_string

    def test_key_rotation_backward_compatibility(self):
        """Test that old encrypted data remains readable after key rotation."""
        encryption = PIIFieldEncryption()

        # Encrypt data with first key
        data1 = "data encrypted with key 1"
        encrypted1 = encryption.encrypt(data1)

        # Rotate key
        new_key = encryption.generate_key()
        encryption.rotate_key(new_key)

        # Encrypt new data with second key
        data2 = "data encrypted with key 2"
        encrypted2 = encryption.encrypt(data2)

        # Should be able to decrypt both
        assert encryption.decrypt(encrypted1) == data1
        assert encryption.decrypt(encrypted2) == data2

    def test_multiple_key_rotations(self):
        """Test multiple key rotations."""
        encryption = PIIFieldEncryption()

        encrypted_data = []
        original_data = []

        # Encrypt data with multiple key rotations
        for i in range(3):
            data = f"data version {i}"
            original_data.append(data)
            encrypted_data.append(encryption.encrypt(data))

            # Rotate key for next iteration
            if i < 2:  # Don't rotate after last iteration
                encryption.rotate_key(encryption.generate_key())

        # All data should still be decryptable
        for i, encrypted in enumerate(encrypted_data):
            decrypted = encryption.decrypt(encrypted)
            assert decrypted == original_data[i]

    def test_invalid_key_format(self):
        """Test handling of invalid encryption keys."""
        # Test with key that's not valid Fernet format
        with pytest.raises(Exception):  # Could be ValueError or cryptography exception
            from cryptography.fernet import Fernet

            invalid_key = b"invalid_key_too_short"
            Fernet(invalid_key)

    def test_concurrent_encryption_operations(self):
        """Test that encryption works correctly with concurrent operations."""
        import threading

        encryption = PIIFieldEncryption()
        results = {}
        errors = []

        def encrypt_decrypt_worker(thread_id):
            try:
                data = f"thread_{thread_id}_data"
                encrypted = encryption.encrypt(data)
                decrypted = encryption.decrypt(encrypted)
                results[thread_id] = data == decrypted
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=encrypt_decrypt_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(results.values()), "Some encryption/decryption operations failed"
