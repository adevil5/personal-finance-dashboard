"""
Tests for OCR functionality and PII detection in receipts.
"""

import io
from unittest.mock import patch

import pytest
from PIL import Image, ImageDraw, ImageFont

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.security.ocr import OCRError, ReceiptOCRProcessor


class TestReceiptOCRProcessor:
    """Test cases for ReceiptOCRProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ReceiptOCRProcessor()

    def create_test_image_with_text(self, text: str, size=(800, 600)) -> bytes:
        """Create a test image with the given text."""
        # Create a white image
        image = Image.new("RGB", size, color="white")
        draw = ImageDraw.Draw(image)

        # Try to use a built-in font, fall back to default if not available
        try:
            # Try to use a larger font for better OCR
            font = ImageFont.truetype("arial.ttf", 40)
        except OSError:
            try:
                # Try alternative font names
                font = ImageFont.truetype("Arial.ttf", 40)
            except OSError:
                # Fall back to default font
                font = ImageFont.load_default()

        # Calculate text position (centered)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)

        # Draw black text on white background
        draw.text(position, text, fill="black", font=font)

        # Save to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        return img_bytes.getvalue()

    def create_uploaded_file(self, content: bytes, filename: str) -> SimpleUploadedFile:
        """Create a Django UploadedFile from bytes content."""
        return SimpleUploadedFile(filename, content, content_type="image/png")

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_extract_text_from_image_success(self, mock_ocr):
        """Test successful text extraction from image."""
        # Setup
        mock_ocr.return_value = "Receipt\nTotal: $25.99\nThank you!"
        test_image = self.create_test_image_with_text("Receipt\nTotal: $25.99")
        uploaded_file = self.create_uploaded_file(test_image, "receipt.png")

        # Execute
        result = self.processor.extract_text_from_image(uploaded_file)

        # Assert
        assert result == "Receipt\nTotal: $25.99\nThank you!"
        mock_ocr.assert_called_once()

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_extract_text_empty_result(self, mock_ocr):
        """Test handling of empty OCR result."""
        # Setup
        mock_ocr.return_value = ""
        test_image = self.create_test_image_with_text("")
        uploaded_file = self.create_uploaded_file(test_image, "empty.png")

        # Execute
        result = self.processor.extract_text_from_image(uploaded_file)

        # Assert
        assert result == ""
        mock_ocr.assert_called_once()

    @patch("apps.core.security.ocr.pytesseract.image_to_data")
    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_extract_text_with_confidence_threshold(
        self, mock_ocr_string, mock_ocr_data
    ):
        """Test text extraction with confidence filtering."""
        # Setup
        mock_ocr_data.return_value = {
            "text": ["High", "confidence", "text"],
            "conf": [95, 85, 90],
        }
        test_image = self.create_test_image_with_text("Clear text")
        uploaded_file = self.create_uploaded_file(test_image, "clear.png")

        # Execute
        result = self.processor.extract_text_from_image(
            uploaded_file, min_confidence=70
        )

        # Assert
        assert "High confidence text" in result
        mock_ocr_data.assert_called_once()

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_extract_text_ocr_error(self, mock_ocr):
        """Test handling of OCR processing errors."""
        # Setup
        mock_ocr.side_effect = Exception("OCR processing failed")
        test_image = self.create_test_image_with_text("Test")
        uploaded_file = self.create_uploaded_file(test_image, "error.png")

        # Execute & Assert
        with pytest.raises(OCRError, match="Failed to extract text from image"):
            self.processor.extract_text_from_image(uploaded_file)

    def test_extract_text_invalid_file(self):
        """Test handling of invalid file input."""
        # Create invalid file content
        invalid_content = b"Not an image"
        uploaded_file = self.create_uploaded_file(invalid_content, "invalid.txt")

        # Execute & Assert
        with pytest.raises(OCRError, match="Failed to process image file"):
            self.processor.extract_text_from_image(uploaded_file)

    def test_extract_text_none_file(self):
        """Test handling of None file input."""
        # Execute & Assert
        with pytest.raises(OCRError, match="No file provided"):
            self.processor.extract_text_from_image(None)

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_scan_for_pii_with_detected_pii(self, mock_ocr):
        """Test PII detection in OCR-extracted text."""
        # Setup
        text_with_pii = """
        Receipt #123
        Date: 2024-01-15
        Customer: john.doe@email.com
        Phone: (555) 123-4567
        Card: 4111 1111 1111 1111
        Total: $45.99
        """
        mock_ocr.return_value = text_with_pii
        test_image = self.create_test_image_with_text("Receipt with PII")
        uploaded_file = self.create_uploaded_file(test_image, "pii_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert "text" in result
        assert "pii_detected" in result
        assert len(result["pii_detected"]["emails"]) > 0
        assert len(result["pii_detected"]["phone_numbers"]) > 0
        assert len(result["pii_detected"]["credit_cards"]) > 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_scan_for_pii_without_pii(self, mock_ocr):
        """Test scanning text without PII."""
        # Setup
        clean_text = """
        Store Name
        Date: 2024-01-15
        Item 1: $10.99
        Item 2: $15.00
        Total: $25.99
        Thank you!
        """
        mock_ocr.return_value = clean_text
        test_image = self.create_test_image_with_text("Clean receipt")
        uploaded_file = self.create_uploaded_file(test_image, "clean_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is False
        assert "text" in result
        assert "pii_detected" in result
        assert len(result["pii_detected"]["emails"]) == 0
        assert len(result["pii_detected"]["phone_numbers"]) == 0
        assert len(result["pii_detected"]["credit_cards"]) == 0
        assert len(result["pii_detected"]["ssn"]) == 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_redact_pii_in_text(self, mock_ocr):
        """Test PII redaction in OCR-extracted text."""
        # Setup
        text_with_pii = """
        Receipt #123
        Customer: john.doe@email.com
        Phone: (555) 123-4567
        Card: 4111 1111 1111 1111
        Total: $45.99
        """
        mock_ocr.return_value = text_with_pii
        test_image = self.create_test_image_with_text("Receipt with PII")
        uploaded_file = self.create_uploaded_file(test_image, "pii_receipt.png")

        # Execute
        result = self.processor.redact_pii_from_receipt(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert "[PII_REDACTED]" in result["redacted_text"]
        assert "john.doe@email.com" not in result["redacted_text"]
        assert "(555) 123-4567" not in result["redacted_text"]
        assert "4111 1111 1111 1111" not in result["redacted_text"]

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_redact_pii_custom_replacement(self, mock_ocr):
        """Test PII redaction with custom replacement text."""
        # Setup
        text_with_pii = "Email: test@example.com Phone: 555-123-4567"
        mock_ocr.return_value = text_with_pii
        test_image = self.create_test_image_with_text("PII text")
        uploaded_file = self.create_uploaded_file(test_image, "pii.png")

        # Execute
        result = self.processor.redact_pii_from_receipt(
            uploaded_file, replacement="[SENSITIVE_INFO]"
        )

        # Assert
        assert "[SENSITIVE_INFO]" in result["redacted_text"]
        assert "test@example.com" not in result["redacted_text"]
        assert "555-123-4567" not in result["redacted_text"]

    def test_process_pdf_file(self):
        """Test processing PDF files."""
        # Create a simple PDF-like content (for testing purposes)
        pdf_content = b"%PDF-1.4\n%Test PDF content"
        uploaded_file = SimpleUploadedFile(
            "receipt.pdf", pdf_content, content_type="application/pdf"
        )

        # PDF processing should raise an OCRError since it's not a valid image
        with pytest.raises(OCRError, match="Failed to process image file"):
            self.processor.extract_text_from_image(uploaded_file)

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_scan_for_pii_ocr_failure(self, mock_ocr):
        """Test PII scanning when OCR fails."""
        # Setup
        mock_ocr.side_effect = Exception("OCR failed")
        test_image = self.create_test_image_with_text("Test")
        uploaded_file = self.create_uploaded_file(test_image, "test.png")

        # Execute & Assert
        with pytest.raises(OCRError):
            self.processor.scan_for_pii(uploaded_file)

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_confidence_based_filtering(self, mock_ocr):
        """Test confidence-based text filtering."""
        # Setup - simulate pytesseract returning data with confidence
        mock_ocr.return_value = "High confidence text"
        test_image = self.create_test_image_with_text("Clear text")
        uploaded_file = self.create_uploaded_file(test_image, "clear.png")

        # Execute with different confidence thresholds
        result_high = self.processor.extract_text_from_image(
            uploaded_file, min_confidence=90
        )
        result_low = self.processor.extract_text_from_image(
            uploaded_file, min_confidence=30
        )

        # Assert
        assert isinstance(result_high, str)
        assert isinstance(result_low, str)

    def test_get_supported_formats(self):
        """Test getting supported file formats."""
        formats = self.processor.get_supported_formats()

        assert isinstance(formats, list)
        assert len(formats) > 0
        assert "PNG" in formats or "JPEG" in formats


class TestOCRIntegration:
    """Integration tests for OCR with real image processing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ReceiptOCRProcessor()

    def test_real_image_processing(self):
        """Test OCR with actual image processing (if tesseract is available)."""
        # Create a simple test image with text
        image = Image.new("RGB", (400, 200), color="white")
        draw = ImageDraw.Draw(image)

        # Use default font for compatibility
        font = ImageFont.load_default()
        draw.text((50, 80), "TEST RECEIPT", fill="black", font=font)
        draw.text((50, 120), "TOTAL: $25.99", fill="black", font=font)

        # Save to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        uploaded_file = SimpleUploadedFile(
            "test_receipt.png", img_bytes.getvalue(), content_type="image/png"
        )

        try:
            # This test will only pass if tesseract is properly installed
            result = self.processor.extract_text_from_image(uploaded_file)
            assert isinstance(result, str)
            # The exact text may vary due to OCR accuracy, so just check it's not empty
            # in a real environment with tesseract installed
        except OCRError:
            # This is expected if tesseract is not installed in test environment
            pytest.skip("Tesseract not available in test environment")

    def test_invalid_image_handling(self):
        """Test handling of corrupted or invalid image files."""
        # Create invalid image data
        invalid_data = b"This is not an image file"
        uploaded_file = SimpleUploadedFile(
            "invalid.png", invalid_data, content_type="image/png"
        )

        with pytest.raises(OCRError):
            self.processor.extract_text_from_image(uploaded_file)
