"""
PII Detection utilities for identifying sensitive data in text.
"""

import re
from typing import Dict, List, Pattern


class PIIDetector:
    """
    Detects various types of Personally Identifiable Information (PII) in text.
    """

    def __init__(self):
        """Initialize the PII detector with common patterns."""
        self._email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )

        self._phone_pattern = re.compile(
            r"(?:\+?1[-.\s]?)?"  # Optional country code
            r"(?:\(?[0-9]{3}\)?[-.\s]?)"  # Area code
            r"[0-9]{3}[-.\s]?"  # First 3 digits
            r"[0-9]{4}\b"  # Last 4 digits with word boundary
        )

        self._ssn_pattern = re.compile(r"\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b")

        # Credit card patterns for major card types
        self._credit_card_pattern = re.compile(
            r"\b(?:"
            r"4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|"  # Visa
            r"5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|"  # Mastercard
            r"3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}|"  # American Express
            r"6(?:011|5\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"  # Discover
            r")\b"
        )

        # International phone pattern (more permissive)
        self._international_phone_pattern = re.compile(
            r"\+\d{1,3}[-.\s]?(?:\d{1,4}[-.\s]?){1,4}\d{1,4}"
        )

        # Custom patterns storage
        self._custom_patterns: Dict[str, Pattern[str]] = {}

    def detect_emails(self, text: str) -> List[str]:
        """
        Detect email addresses in text.

        Args:
            text: Text to scan for email addresses

        Returns:
            List of detected email addresses
        """
        if not text:
            return []
        return self._email_pattern.findall(text)

    def detect_phone_numbers(self, text: str) -> List[str]:
        """
        Detect phone numbers in text (US and international formats).

        Args:
            text: Text to scan for phone numbers

        Returns:
            List of detected phone numbers
        """
        if not text:
            return []

        # Find US phone numbers
        us_phones = self._phone_pattern.findall(text)

        # Find international phone numbers
        intl_phones = self._international_phone_pattern.findall(text)

        # Combine and remove duplicates
        all_phones = list(set(us_phones + intl_phones))

        # Filter out numbers that are too short or too long
        valid_phones = []
        for phone in all_phones:
            # Remove non-digit characters for length check
            digits_only = re.sub(r"[^\d]", "", phone)
            if 10 <= len(digits_only) <= 15:  # Valid phone number length
                valid_phones.append(phone)

        return valid_phones

    def detect_ssn(self, text: str) -> List[str]:
        """
        Detect Social Security Numbers in text.

        Args:
            text: Text to scan for SSNs

        Returns:
            List of detected SSNs
        """
        if not text:
            return []
        return self._ssn_pattern.findall(text)

    def detect_credit_cards(self, text: str) -> List[str]:
        """
        Detect credit card numbers in text.

        Args:
            text: Text to scan for credit card numbers

        Returns:
            List of detected credit card numbers
        """
        if not text:
            return []

        potential_cards = self._credit_card_pattern.findall(text)

        # Validate using Luhn algorithm
        valid_cards = []
        for card in potential_cards:
            # Remove spaces and dashes
            card_digits = re.sub(r"[-\s]", "", card)
            if self._luhn_check(card_digits):
                valid_cards.append(card)

        return valid_cards

    def detect_all(self, text: str) -> Dict[str, List[str]]:
        """
        Detect all types of PII in text.

        Args:
            text: Text to scan for PII

        Returns:
            Dictionary with PII types as keys and lists of detected items as values
        """
        return {
            "emails": self.detect_emails(text),
            "phone_numbers": self.detect_phone_numbers(text),
            "ssn": self.detect_ssn(text),
            "credit_cards": self.detect_credit_cards(text),
        }

    def has_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.

        Args:
            text: Text to check

        Returns:
            True if any PII is detected, False otherwise
        """
        if not text:
            return False

        all_pii = self.detect_all(text)
        return any(len(pii_list) > 0 for pii_list in all_pii.values())

    def add_custom_pattern(self, name: str, pattern: str) -> None:
        """
        Add a custom PII detection pattern.

        Args:
            name: Name for the custom pattern
            pattern: Regular expression pattern
        """
        self._custom_patterns[name] = re.compile(pattern)

    def detect_custom(self, pattern_name: str, text: str) -> List[str]:
        """
        Detect PII using a custom pattern.

        Args:
            pattern_name: Name of the custom pattern to use
            text: Text to scan

        Returns:
            List of matches for the custom pattern
        """
        if pattern_name not in self._custom_patterns:
            raise ValueError(f"Custom pattern '{pattern_name}' not found")

        if not text:
            return []

        return self._custom_patterns[pattern_name].findall(text)

    def _luhn_check(self, card_number: str) -> bool:
        """
        Validate credit card number using Luhn algorithm.

        Args:
            card_number: Credit card number as string (digits only)

        Returns:
            True if valid according to Luhn algorithm, False otherwise
        """
        if not card_number.isdigit():
            return False

        # Convert to list of integers, reverse for easier processing
        digits = [int(d) for d in card_number[::-1]]

        # Apply Luhn algorithm
        checksum = 0
        for i, digit in enumerate(digits):
            if i % 2 == 1:  # Every second digit (from right)
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def get_pattern_info(self) -> Dict[str, str]:
        """
        Get information about available detection patterns.

        Returns:
            Dictionary with pattern names and descriptions
        """
        patterns = {
            "emails": "Email addresses (user@domain.com)",
            "phone_numbers": "US and international phone numbers",
            "ssn": "Social Security Numbers (XXX-XX-XXXX or XXXXXXXXX)",
            "credit_cards": "Credit card numbers (Visa, Mastercard, Amex, Discover)",
        }

        # Add custom patterns
        for name in self._custom_patterns:
            patterns[f"custom_{name}"] = f"Custom pattern: {name}"

        return patterns

    def validate_email(self, email: str) -> bool:
        """
        Validate if a string is a properly formatted email.

        Args:
            email: Email string to validate

        Returns:
            True if valid email format, False otherwise
        """
        if not email:
            return False

        matches = self._email_pattern.findall(email)
        return len(matches) == 1 and matches[0] == email

    def validate_phone(self, phone: str) -> bool:
        """
        Validate if a string is a properly formatted phone number.

        Args:
            phone: Phone string to validate

        Returns:
            True if valid phone format, False otherwise
        """
        if not phone:
            return False

        # Check if it matches our phone patterns
        us_match = self._phone_pattern.search(phone)
        intl_match = self._international_phone_pattern.search(phone)

        if us_match or intl_match:
            # Ensure the entire string is a phone number
            digits_only = re.sub(r"[^\d]", "", phone)
            return 10 <= len(digits_only) <= 15

        return False

    def sanitize_for_logging(
        self, text: str, replacement: str = "[PII_DETECTED]"
    ) -> str:
        """
        Sanitize text for safe logging by replacing detected PII.

        Args:
            text: Text to sanitize
            replacement: String to replace PII with

        Returns:
            Sanitized text safe for logging
        """
        if not text:
            return text

        sanitized = text

        # Replace emails
        sanitized = self._email_pattern.sub(replacement, sanitized)

        # Replace phone numbers
        sanitized = self._phone_pattern.sub(replacement, sanitized)
        sanitized = self._international_phone_pattern.sub(replacement, sanitized)

        # Replace SSNs
        sanitized = self._ssn_pattern.sub(replacement, sanitized)

        # Replace credit cards
        sanitized = self._credit_card_pattern.sub(replacement, sanitized)

        return sanitized
