"""
Data masking utilities for PII protection in non-production environments.
"""

import re
from typing import Optional

from .pii_detection import PIIDetector


class PIIMasker:
    """
    Masks PII data in text for safe display in non-production environments.
    """

    def __init__(self, mask_char: str = "*", partial_mask: bool = False):
        """
        Initialize the PII masker.

        Args:
            mask_char: Character to use for masking
            partial_mask: If True, show partial data (e.g., domain in emails)
        """
        self.mask_char = mask_char
        self.partial_mask = partial_mask
        self.detector = PIIDetector()

    def mask_emails(self, text: str) -> str:
        """
        Mask email addresses in text.

        Args:
            text: Text containing emails to mask

        Returns:
            Text with emails masked
        """
        if not text:
            return text

        def mask_email(match):
            email = match.group(0)
            if self.partial_mask:
                # Show domain, mask username
                username, domain = email.split("@", 1)
                masked_username = self.mask_char * min(len(username), 3)
                return f"{masked_username}@{domain}"
            else:
                # Mask most of the email but preserve structure
                if "@" in email:
                    username, domain = email.split("@", 1)
                    return f"{self.mask_char * 3}@{self.mask_char * 3}.com"
                return self.mask_char * len(email)

        return self.detector._email_pattern.sub(mask_email, text)

    def mask_phone_numbers(self, text: str) -> str:
        """
        Mask phone numbers in text.

        Args:
            text: Text containing phone numbers to mask

        Returns:
            Text with phone numbers masked
        """
        if not text:
            return text

        def mask_phone(match):
            phone = match.group(0)
            if self.partial_mask:
                # Keep format but mask digits
                return re.sub(r"\d", self.mask_char, phone)
            else:
                # Replace with simple mask
                return self.mask_char * 3

        # Mask both US and international patterns
        text = self.detector._phone_pattern.sub(mask_phone, text)
        text = self.detector._international_phone_pattern.sub(mask_phone, text)

        return text

    def mask_ssn(self, text: str) -> str:
        """
        Mask Social Security Numbers in text.

        Args:
            text: Text containing SSNs to mask

        Returns:
            Text with SSNs masked
        """
        if not text:
            return text

        def mask_ssn(match):
            ssn = match.group(0)
            if "-" in ssn:
                return f"{self.mask_char * 3}-{self.mask_char * 2}-{self.mask_char * 4}"
            else:
                return self.mask_char * len(ssn)

        return self.detector._ssn_pattern.sub(mask_ssn, text)

    def mask_credit_cards(self, text: str) -> str:
        """
        Mask credit card numbers in text.

        Args:
            text: Text containing credit card numbers to mask

        Returns:
            Text with credit card numbers masked
        """
        if not text:
            return text

        def mask_card(match):
            card = match.group(0)
            # Remove spaces/dashes for processing
            card_digits = re.sub(r"[-\s]", "", card)

            if self.partial_mask and len(card_digits) >= 4:
                # Show last 4 digits
                masked_part = self.mask_char * (len(card_digits) - 4)
                last_four = card_digits[-4:]

                # Preserve original formatting
                if "-" in card:
                    return (
                        f"{self.mask_char * 4}-{self.mask_char * 4}-"
                        f"{self.mask_char * 4}-{last_four}"
                    )
                elif " " in card:
                    return (
                        f"{self.mask_char * 4} {self.mask_char * 4} "
                        f"{self.mask_char * 4} {last_four}"
                    )
                else:
                    return masked_part + last_four
            else:
                # Mask entire number
                return self.mask_char * 4

        return self.detector._credit_card_pattern.sub(mask_card, text)

    def mask_all(self, text: str) -> str:
        """
        Mask all types of PII in text.

        Args:
            text: Text to mask

        Returns:
            Text with all PII masked
        """
        if not text:
            return text

        # Apply all masking functions
        masked = self.mask_emails(text)
        masked = self.mask_phone_numbers(masked)
        masked = self.mask_ssn(masked)
        masked = self.mask_credit_cards(masked)

        return masked

    def mask_custom_pattern(
        self, text: str, pattern_name: str, replacement: Optional[str] = None
    ) -> str:
        """
        Mask text using a custom pattern.

        Args:
            text: Text to mask
            pattern_name: Name of custom pattern to use
            replacement: Custom replacement string (defaults to mask_char * 3)

        Returns:
            Text with custom pattern masked
        """
        if not text or pattern_name not in self.detector._custom_patterns:
            return text

        if replacement is None:
            replacement = self.mask_char * 3

        pattern = self.detector._custom_patterns[pattern_name]
        return pattern.sub(replacement, text)


# Standalone utility functions for specific masking needs


def mask_email(email: str, partial: bool = False, mask_char: str = "*") -> str:
    """
    Mask a single email address.

    Args:
        email: Email to mask
        partial: If True, show domain
        mask_char: Character to use for masking

    Returns:
        Masked email
    """
    if not email:
        return ""

    # Simple email validation
    if "@" not in email:
        return email

    try:
        username, domain = email.split("@", 1)
        if partial:
            masked_username = mask_char * min(len(username), 3)
            return f"{masked_username}@{domain}"
        else:
            return f"{mask_char * 3}@{mask_char * 3}.com"
    except ValueError:
        return email


def mask_phone(phone: str, preserve_format: bool = False, mask_char: str = "*") -> str:
    """
    Mask a single phone number.

    Args:
        phone: Phone number to mask
        preserve_format: If True, preserve original formatting
        mask_char: Character to use for masking

    Returns:
        Masked phone number
    """
    if not phone:
        return ""

    # Check if it looks like a valid phone number (at least 10 digits)
    digits_only = re.sub(r"[^\d]", "", phone)
    if len(digits_only) < 10:
        return phone  # Return unchanged if too short

    if preserve_format:
        # Replace digits with mask character
        return re.sub(r"\d", mask_char, phone)
    else:
        return mask_char * 3


def mask_ssn(ssn: str, mask_char: str = "*") -> str:
    """
    Mask a single Social Security Number.

    Args:
        ssn: SSN to mask
        mask_char: Character to use for masking

    Returns:
        Masked SSN
    """
    if not ssn:
        return ""

    if len(ssn) == 9 and ssn.isdigit():
        return mask_char * 9
    elif len(ssn) == 11 and ssn.count("-") == 2:
        return f"{mask_char * 3}-{mask_char * 2}-{mask_char * 4}"
    else:
        # Invalid format, return as-is
        return ssn


def mask_credit_card(
    card: str, show_last_four: bool = True, mask_char: str = "*"
) -> str:
    """
    Mask a single credit card number.

    Args:
        card: Credit card number to mask
        show_last_four: If True, show last 4 digits
        mask_char: Character to use for masking

    Returns:
        Masked credit card number
    """
    if not card:
        return ""

    # Remove spaces and dashes for processing
    card_digits = re.sub(r"[-\s]", "", card)

    if not card_digits.isdigit() or len(card_digits) < 4:
        return card

    if show_last_four:
        last_four = card_digits[-4:]
        # Preserve original formatting
        if "-" in card:
            return f"{mask_char * 4}-{mask_char * 4}-{mask_char * 4}-{last_four}"
        elif " " in card:
            return f"{mask_char * 4} {mask_char * 4} {mask_char * 4} {last_four}"
        else:
            masked_part = mask_char * (len(card_digits) - 4)
            return masked_part + last_four
    else:
        return mask_char * len(card_digits)


class DataMasker:
    """
    Utility class for masking entire datasets in non-production environments.
    """

    def __init__(self, environment: str = "development"):
        """
        Initialize data masker.

        Args:
            environment: Environment name (production data is never masked)
        """
        self.environment = environment
        self.should_mask = environment.lower() != "production"
        self.masker = PIIMasker(partial_mask=True)

    def mask_user_data(self, user_data: dict) -> dict:
        """
        Mask sensitive fields in user data dictionary.

        Args:
            user_data: Dictionary containing user data

        Returns:
            Dictionary with sensitive fields masked
        """
        if not self.should_mask:
            return user_data

        masked_data = user_data.copy()

        # Fields to mask
        sensitive_fields = ["email", "phone", "ssn", "first_name", "last_name"]

        for field in sensitive_fields:
            if field in masked_data:
                value = masked_data[field]
                if isinstance(value, str):
                    if field == "email":
                        masked_data[field] = mask_email(value, partial=True)
                    elif field == "phone":
                        masked_data[field] = mask_phone(value)
                    elif field == "ssn":
                        masked_data[field] = mask_ssn(value)
                    elif field in ["first_name", "last_name"]:
                        # Mask names
                        masked_data[field] = (
                            value[0] + "*" * (len(value) - 1) if value else value
                        )

        return masked_data

    def mask_financial_data(self, financial_data: dict) -> dict:
        """
        Mask sensitive fields in financial data.

        Args:
            financial_data: Dictionary containing financial data

        Returns:
            Dictionary with sensitive amounts and account info masked
        """
        if not self.should_mask:
            return financial_data

        masked_data = financial_data.copy()

        # Fields to mask
        amount_fields = ["amount", "balance", "monthly_income", "budget_amount"]
        account_fields = ["account_number", "routing_number"]

        for field in amount_fields:
            if field in masked_data and masked_data[field] is not None:
                # Mask financial amounts by rounding to nearest $100
                if isinstance(masked_data[field], (int, float)):
                    original = float(masked_data[field])
                    masked_data[field] = round(original / 100) * 100

        for field in account_fields:
            if field in masked_data and masked_data[field]:
                value = str(masked_data[field])
                # Show last 4 digits of account numbers
                if len(value) > 4:
                    masked_data[field] = "*" * (len(value) - 4) + value[-4:]

        return masked_data

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return not self.should_mask
