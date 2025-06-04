"""
Tests for PII detection and masking utilities.
"""

from apps.core.security.masking import (
    PIIMasker,
    mask_credit_card,
    mask_email,
    mask_phone,
    mask_ssn,
)
from apps.core.security.pii_detection import PIIDetector


class TestPIIDetector:
    """Test cases for PIIDetector class."""

    def test_detector_creation(self):
        """Test that PIIDetector can be instantiated."""
        detector = PIIDetector()
        assert detector is not None

    def test_detect_email_addresses(self):
        """Test detection of email addresses."""
        detector = PIIDetector()

        # Valid email addresses
        text = "Contact us at support@example.com or admin@test.org"
        results = detector.detect_emails(text)
        assert len(results) == 2
        assert "support@example.com" in results
        assert "admin@test.org" in results

    def test_detect_phone_numbers(self):
        """Test detection of phone numbers in various formats."""
        detector = PIIDetector()

        # Various phone number formats
        text = "Call us at (555) 123-4567 or 555.987.6543 or +1-555-555-1234"
        results = detector.detect_phone_numbers(text)
        assert len(results) == 3
        assert "(555) 123-4567" in results
        assert "555.987.6543" in results
        assert "+1-555-555-1234" in results

    def test_detect_ssn(self):
        """Test detection of Social Security Numbers."""
        detector = PIIDetector()

        # SSN formats
        text = "SSN: 123-45-6789 or 987654321"
        results = detector.detect_ssn(text)
        assert len(results) == 2
        assert "123-45-6789" in results
        assert "987654321" in results

    def test_detect_credit_cards(self):
        """Test detection of credit card numbers."""
        detector = PIIDetector()

        # Credit card numbers (using test numbers)
        text = "Card: 4111111111111111 or 5555-5555-5555-4444"
        results = detector.detect_credit_cards(text)
        assert len(results) == 2
        assert "4111111111111111" in results
        assert "5555-5555-5555-4444" in results

    def test_detect_all_pii(self):
        """Test detection of all PII types in one call."""
        detector = PIIDetector()

        text = """
        Contact John Doe at john.doe@example.com or (555) 123-4567.
        His SSN is 123-45-6789 and credit card is 4111-1111-1111-1111.
        """

        results = detector.detect_all(text)
        assert "emails" in results
        assert "phone_numbers" in results
        assert "ssn" in results
        assert "credit_cards" in results

        assert len(results["emails"]) == 1
        assert len(results["phone_numbers"]) == 1
        assert len(results["ssn"]) == 1
        assert len(results["credit_cards"]) == 1

    def test_detect_no_pii(self):
        """Test that no PII is detected in clean text."""
        detector = PIIDetector()

        text = "This is just a normal sentence with no sensitive data."
        results = detector.detect_all(text)

        assert len(results["emails"]) == 0
        assert len(results["phone_numbers"]) == 0
        assert len(results["ssn"]) == 0
        assert len(results["credit_cards"]) == 0

    def test_detect_partial_matches(self):
        """Test that partial matches are not detected as PII."""
        detector = PIIDetector()

        # These should not be detected as valid PII
        text = "Call 555-12 or email @example or card 4111"
        results = detector.detect_all(text)

        assert len(results["emails"]) == 0
        assert len(results["phone_numbers"]) == 0
        assert len(results["credit_cards"]) == 0

    def test_detect_mixed_case_emails(self):
        """Test detection of emails with mixed case."""
        detector = PIIDetector()

        text = "Contact Test@Example.COM or ADMIN@test.ORG"
        results = detector.detect_emails(text)
        assert len(results) == 2

    def test_detect_international_phone(self):
        """Test detection of international phone numbers."""
        detector = PIIDetector()

        text = "International: +44 20 7946 0958 or +33 1 42 86 83 26"
        results = detector.detect_phone_numbers(text)
        assert len(results) >= 1  # Should detect at least one international number

    def test_has_pii_method(self):
        """Test convenience method to check if text contains any PII."""
        detector = PIIDetector()

        # Text with PII
        pii_text = "Email me at test@example.com"
        assert detector.has_pii(pii_text) is True

        # Text without PII
        clean_text = "This is clean text"
        assert detector.has_pii(clean_text) is False

    def test_custom_patterns(self):
        """Test adding custom PII detection patterns."""
        detector = PIIDetector()

        # Add custom pattern for account numbers
        account_pattern = r"\b\d{10,12}\b"
        detector.add_custom_pattern("account_numbers", account_pattern)

        text = "Account number: 1234567890"  # 10 digits
        results = detector.detect_custom("account_numbers", text)
        assert len(results) == 1
        assert "1234567890" in results


class TestPIIMasker:
    """Test cases for PIIMasker class."""

    def test_masker_creation(self):
        """Test that PIIMasker can be instantiated."""
        masker = PIIMasker()
        assert masker is not None

    def test_mask_email_addresses(self):
        """Test masking of email addresses."""
        masker = PIIMasker()

        text = "Contact us at john.doe@example.com for support"
        masked = masker.mask_emails(text)
        assert "john.doe@example.com" not in masked
        assert "***@***.com" in masked or "j***@e***.com" in masked

    def test_mask_phone_numbers(self):
        """Test masking of phone numbers."""
        masker = PIIMasker()

        text = "Call us at (555) 123-4567"
        masked = masker.mask_phone_numbers(text)
        assert "(555) 123-4567" not in masked
        assert "***" in masked

    def test_mask_ssn(self):
        """Test masking of Social Security Numbers."""
        masker = PIIMasker()

        text = "SSN: 123-45-6789"
        masked = masker.mask_ssn(text)
        assert "123-45-6789" not in masked
        assert "***-**-****" in masked

    def test_mask_credit_cards(self):
        """Test masking of credit card numbers."""
        masker = PIIMasker()

        text = "Card: 4111111111111111"
        masked = masker.mask_credit_cards(text)
        assert "4111111111111111" not in masked
        assert "****" in masked

    def test_mask_all_pii(self):
        """Test masking all PII types in one call."""
        masker = PIIMasker()

        text = """
        Contact John at john@example.com or (555) 123-4567.
        SSN: 123-45-6789, Card: 4111111111111111
        """

        masked = masker.mask_all(text)
        assert "john@example.com" not in masked
        assert "(555) 123-4567" not in masked
        assert "123-45-6789" not in masked
        assert "4111111111111111" not in masked

    def test_preserve_structure(self):
        """Test that masking preserves text structure."""
        masker = PIIMasker()

        original = "Email: test@example.com\nPhone: (555) 123-4567"
        masked = masker.mask_all(original)

        # Should preserve line breaks and basic structure
        assert "\n" in masked
        assert "Email:" in masked
        assert "Phone:" in masked

    def test_custom_mask_character(self):
        """Test using custom masking character."""
        masker = PIIMasker(mask_char="X")

        text = "Email: test@example.com"
        masked = masker.mask_emails(text)
        assert "X" in masked
        assert "*" not in masked

    def test_partial_masking_email(self):
        """Test partial masking of emails (showing domain)."""
        masker = PIIMasker(partial_mask=True)

        text = "Contact: john.doe@example.com"
        masked = masker.mask_emails(text)
        # Should show domain but mask username
        assert "@example.com" in masked
        assert "john.doe" not in masked

    def test_no_pii_unchanged(self):
        """Test that text without PII remains unchanged."""
        masker = PIIMasker()

        text = "This is just normal text with no sensitive data."
        masked = masker.mask_all(text)
        assert masked == text


class TestMaskingUtilities:
    """Test cases for individual masking utility functions."""

    def test_mask_email_function(self):
        """Test standalone email masking function."""
        email = "john.doe@example.com"
        masked = mask_email(email)
        assert email not in masked
        assert "@" in masked

    def test_mask_phone_function(self):
        """Test standalone phone masking function."""
        phone = "(555) 123-4567"
        masked = mask_phone(phone)
        assert phone not in masked
        assert "***" in masked

    def test_mask_ssn_function(self):
        """Test standalone SSN masking function."""
        ssn = "123-45-6789"
        masked = mask_ssn(ssn)
        assert ssn not in masked
        assert "***-**-****" == masked

    def test_mask_credit_card_function(self):
        """Test standalone credit card masking function."""
        card = "4111111111111111"
        masked = mask_credit_card(card)
        assert card not in masked
        # Should show last 4 digits
        assert "1111" in masked
        assert "****" in masked

    def test_mask_credit_card_with_dashes(self):
        """Test credit card masking with dashes."""
        card = "4111-1111-1111-1111"
        masked = mask_credit_card(card)
        assert card not in masked
        assert "1111" in masked
        assert "****-****-****-1111" == masked

    def test_mask_email_partial(self):
        """Test partial email masking."""
        email = "john.doe@example.com"
        masked = mask_email(email, partial=True)
        assert "john.doe" not in masked
        assert "@example.com" in masked

    def test_mask_phone_preserve_format(self):
        """Test phone masking while preserving format."""
        phone = "(555) 123-4567"
        masked = mask_phone(phone, preserve_format=True)
        assert "(***) ***-****" == masked

    def test_empty_string_masking(self):
        """Test masking empty or None values."""
        assert mask_email("") == ""
        assert mask_email(None) == ""
        assert mask_phone("") == ""
        assert mask_ssn("") == ""
        assert mask_credit_card("") == ""

    def test_invalid_input_masking(self):
        """Test masking invalid inputs."""
        # These should not crash but return the input unchanged or masked
        assert mask_email("not-an-email") == "not-an-email"
        assert mask_phone("123") == "123"  # Too short to be a valid phone
        assert mask_ssn("123") == "123"  # Too short to be valid SSN

    def test_mask_multiple_occurrences(self):
        """Test masking multiple occurrences of the same PII type."""
        masker = PIIMasker()

        text = "Emails: test1@example.com and test2@example.com"
        masked = masker.mask_emails(text)
        assert "test1@example.com" not in masked
        assert "test2@example.com" not in masked
        assert masked.count("***") >= 2 or "@" in masked

    def test_case_insensitive_detection(self):
        """Test that detection and masking work regardless of case."""
        masker = PIIMasker()

        text = "Email: TEST@EXAMPLE.COM"
        masked = masker.mask_emails(text)
        assert "TEST@EXAMPLE.COM" not in masked

    def test_unicode_handling(self):
        """Test handling of unicode characters in text."""
        masker = PIIMasker()

        text = "Contact café owner at test@example.com for résumé"
        masked = masker.mask_emails(text)
        assert "café" in masked  # Non-PII unicode preserved
        assert "résumé" in masked  # Non-PII unicode preserved
        assert "test@example.com" not in masked

    def test_large_text_performance(self):
        """Test masking performance with large text."""
        masker = PIIMasker()

        # Create large text with scattered PII
        base_text = "Some normal text. " * 1000
        large_text = base_text + "Email: test@example.com" + base_text

        masked = masker.mask_all(large_text)
        assert "test@example.com" not in masked
        assert len(masked) > 0

    def test_regex_edge_cases(self):
        """Test edge cases that might break regex patterns."""
        masker = PIIMasker()

        # Text with special regex characters
        text = "Email: test@exam.ple.com [brackets] (parens) {braces}"
        masked = masker.mask_emails(text)
        assert "test@exam.ple.com" not in masked
        assert "[brackets]" in masked  # Non-PII preserved
        assert "(parens)" in masked
        assert "{braces}" in masked
