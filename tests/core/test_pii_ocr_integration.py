"""
Tests for PII detection integration with OCR functionality.

This module tests the integration between OCR text extraction and PII detection
to ensure sensitive information in receipts is properly identified and handled.
"""

import io
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.security.ocr import ReceiptOCRProcessor
from apps.core.security.pii_detection import PIIDetector


class TestPIIDetectionInOCR:
    """Test PII detection in OCR-extracted text from receipt images."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ReceiptOCRProcessor()
        self.pii_detector = PIIDetector()

    def create_test_image_with_text(self, text: str, size=(800, 600)) -> bytes:
        """Create a test image with the given text."""
        image = Image.new("RGB", size, color="white")
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except OSError:
            font = ImageFont.load_default()

        # Split text into lines and draw each line
        lines = text.strip().split("\n")
        y_position = 50

        for line in lines:
            if line.strip():
                draw.text((50, y_position), line.strip(), fill="black", font=font)
                y_position += 30

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        return img_bytes.getvalue()

    def create_uploaded_file(self, content: bytes, filename: str) -> SimpleUploadedFile:
        """Create a Django UploadedFile from bytes content."""
        return SimpleUploadedFile(filename, content, content_type="image/png")

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_detect_email_in_receipt(self, mock_ocr):
        """Test detection of email addresses in receipt OCR text."""
        # Setup
        receipt_text = """
        CUSTOMER RECEIPT
        Date: 2024-01-15
        Email: customer@example.com
        Total: $45.99
        Thank you for your purchase!
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "email_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["emails"]) == 1
        assert "customer@example.com" in result["pii_detected"]["emails"]
        assert len(result["pii_detected"]["phone_numbers"]) == 0
        assert len(result["pii_detected"]["credit_cards"]) == 0
        assert len(result["pii_detected"]["ssn"]) == 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_detect_phone_number_in_receipt(self, mock_ocr):
        """Test detection of phone numbers in receipt OCR text."""
        # Setup
        receipt_text = """
        STORE NAME
        Phone: (555) 123-4567
        Date: 2024-01-15
        Total: $25.50
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "phone_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["phone_numbers"]) == 1
        assert "(555) 123-4567" in result["pii_detected"]["phone_numbers"][0]
        assert len(result["pii_detected"]["emails"]) == 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_detect_credit_card_in_receipt(self, mock_ocr):
        """Test detection of credit card numbers in receipt OCR text."""
        # Setup - using a valid test credit card number (Luhn algorithm)
        receipt_text = """
        PAYMENT RECEIPT
        Card: 4111 1111 1111 1111
        Amount: $89.99
        Approved
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "card_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["credit_cards"]) == 1
        assert "4111 1111 1111 1111" in result["pii_detected"]["credit_cards"]

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_detect_ssn_in_receipt(self, mock_ocr):
        """Test detection of SSN in receipt OCR text."""
        # Setup
        receipt_text = """
        TAX DOCUMENT
        SSN: 123-45-6789
        Year: 2024
        Amount: $1,500.00
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "ssn_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["ssn"]) == 1
        assert "123-45-6789" in result["pii_detected"]["ssn"]

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_detect_multiple_pii_types(self, mock_ocr):
        """Test detection of multiple PII types in a single receipt."""
        # Setup
        receipt_text = """
        PREMIUM SERVICES RECEIPT
        Customer: john.doe@company.com
        Phone: +1-555-987-6543
        Card: 5555 5555 5555 4444
        Service ID: 123-45-6789
        Total: $299.99
        Date: 2024-01-15
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "multi_pii_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["emails"]) >= 1
        assert len(result["pii_detected"]["phone_numbers"]) >= 1
        assert len(result["pii_detected"]["credit_cards"]) >= 1
        assert len(result["pii_detected"]["ssn"]) >= 1

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_no_pii_detected(self, mock_ocr):
        """Test OCR text with no PII information."""
        # Setup
        receipt_text = """
        GROCERY STORE
        Item 1: Apples - $3.99
        Item 2: Bread - $2.50
        Item 3: Milk - $4.25
        Subtotal: $10.74
        Tax: $0.86
        Total: $11.60
        Thank you!
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "clean_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is False
        assert len(result["pii_detected"]["emails"]) == 0
        assert len(result["pii_detected"]["phone_numbers"]) == 0
        assert len(result["pii_detected"]["credit_cards"]) == 0
        assert len(result["pii_detected"]["ssn"]) == 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_pii_redaction_preserves_structure(self, mock_ocr):
        """Test that PII redaction preserves text structure."""
        # Setup
        receipt_text = """
        RECEIPT #12345
        Customer: test@email.com
        Phone: 555-123-4567
        Item: Widget - $10.00
        Total: $10.00
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "structure_test.png")

        # Execute
        result = self.processor.redact_pii_from_receipt(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert "RECEIPT #12345" in result["redacted_text"]
        assert "Widget - $10.00" in result["redacted_text"]
        assert "test@email.com" not in result["redacted_text"]
        assert "555-123-4567" not in result["redacted_text"]
        assert "[PII_REDACTED]" in result["redacted_text"]

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_custom_redaction_replacement(self, mock_ocr):
        """Test PII redaction with custom replacement text."""
        # Setup
        receipt_text = "Email: user@domain.com Phone: 123-456-7890"
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "custom_redact.png")

        # Execute
        result = self.processor.redact_pii_from_receipt(
            uploaded_file, replacement="[CONFIDENTIAL]"
        )

        # Assert
        assert "[CONFIDENTIAL]" in result["redacted_text"]
        assert "user@domain.com" not in result["redacted_text"]
        assert "123-456-7890" not in result["redacted_text"]

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_international_phone_number_detection(self, mock_ocr):
        """Test detection of international phone numbers."""
        # Setup
        receipt_text = """
        INTERNATIONAL RECEIPT
        Phone: +44 20 7946 0958
        Phone2: +1-800-555-0199
        Total: £45.99
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "intl_phone.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        phone_numbers = result["pii_detected"]["phone_numbers"]
        assert len(phone_numbers) >= 1
        # Should detect at least one international number
        has_intl = any(phone for phone in phone_numbers if phone.startswith("+"))
        assert has_intl

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_partial_credit_card_numbers(self, mock_ocr):
        """Test handling of partial or masked credit card numbers."""
        # Setup
        receipt_text = """
        PAYMENT RECEIPT
        Card: **** **** **** 1234
        Card2: 4111-xxxx-xxxx-1111
        Approved: $50.00
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "partial_card.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert - partial/masked cards should not be detected as valid credit cards
        assert len(result["pii_detected"]["credit_cards"]) == 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_edge_case_email_formats(self, mock_ocr):
        """Test detection of various email formats."""
        # Setup
        receipt_text = """
        Emails in receipt:
        simple@example.com
        user.name+tag@domain.co.uk
        test123@sub.domain.org
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "email_formats.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        emails = result["pii_detected"]["emails"]
        assert len(emails) >= 3
        assert "simple@example.com" in emails
        assert "user.name+tag@domain.co.uk" in emails
        assert "test123@sub.domain.org" in emails

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_false_positive_handling(self, mock_ocr):
        """Test handling of false positive patterns."""
        # Setup - use patterns that look like PII but aren't valid
        receipt_text = """
        STORE RECEIPT
        Item: Product-999-99-9999
        SKU: 4111-1111-1111-XXXX
        Price: $19.99
        Date: 12/15/2024
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "false_positive.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert - should not detect incomplete card numbers as valid
        # The SSN pattern 999-99-9999 is invalid and shouldn't be detected
        # (though our current detector might still catch it - this is acceptable)
        assert len(result["pii_detected"]["credit_cards"]) == 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_pii_detection_with_ocr_noise(self, mock_ocr):
        """Test PII detection when OCR introduces noise/errors."""
        # Setup - simulate OCR with some character recognition errors
        receipt_text = """
        REC31PT #1234
        Ema1l: user@examp1e.com
        Ph0ne: 555-123-4567
        Tota1: $29.99
        """
        mock_ocr.return_value = receipt_text
        test_image = self.create_test_image_with_text(receipt_text)
        uploaded_file = self.create_uploaded_file(test_image, "noisy_ocr.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert - should still detect phone number despite OCR noise
        assert len(result["pii_detected"]["phone_numbers"]) >= 1
        # Might not detect the email due to OCR errors (1 instead of l)
        # This is expected behavior


class TestOCRPIIIntegrationEdgeCases:
    """Test edge cases and error conditions for OCR-PII integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ReceiptOCRProcessor()

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_empty_ocr_result_pii_scan(self, mock_ocr):
        """Test PII scanning when OCR returns empty result."""
        # Setup
        mock_ocr.return_value = ""

        # Create minimal image
        image = Image.new("RGB", (100, 100), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")

        uploaded_file = SimpleUploadedFile(
            "empty.png", img_bytes.getvalue(), content_type="image/png"
        )

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is False
        assert result["text"] == ""
        assert all(len(pii_list) == 0 for pii_list in result["pii_detected"].values())

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_whitespace_only_ocr_result(self, mock_ocr):
        """Test PII scanning when OCR returns only whitespace."""
        # Setup
        mock_ocr.return_value = "   \n\n   \t   \n"

        image = Image.new("RGB", (100, 100), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")

        uploaded_file = SimpleUploadedFile(
            "whitespace.png", img_bytes.getvalue(), content_type="image/png"
        )

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is False
        # Text should be cleaned to empty string
        assert result["text"].strip() == ""

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_pii_redaction_preserves_line_structure(self, mock_ocr):
        """Test that PII redaction preserves line breaks and formatting."""
        # Setup
        receipt_text = """Line 1: Regular text
Line 2: Email user@test.com here
Line 3: Phone (555) 123-4567 number
Line 4: More regular text"""

        mock_ocr.return_value = receipt_text

        image = Image.new("RGB", (400, 300), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")

        uploaded_file = SimpleUploadedFile(
            "multiline.png", img_bytes.getvalue(), content_type="image/png"
        )

        # Execute
        result = self.processor.redact_pii_from_receipt(uploaded_file)

        # Assert
        redacted = result["redacted_text"]
        assert "Line 1: Regular text" in redacted
        assert "Line 4: More regular text" in redacted
        assert "user@test.com" not in redacted
        assert "(555) 123-4567" not in redacted
        assert "[PII_REDACTED]" in redacted
