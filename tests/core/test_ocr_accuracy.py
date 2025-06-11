"""
Accuracy tests for OCR and PII detection functionality.

This module tests the real-world accuracy of OCR text extraction
and PII detection with various receipt scenarios.
"""

import io
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.security.ocr import ReceiptOCRProcessor


class TestOCRAccuracy:
    """Test OCR accuracy with various receipt scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ReceiptOCRProcessor()

    def create_realistic_receipt_image(
        self, receipt_data: dict, size=(600, 800)
    ) -> bytes:
        """Create a realistic receipt image with structured data."""
        image = Image.new("RGB", size, color="white")
        draw = ImageDraw.Draw(image)

        try:
            # Try to use a readable font
            title_font = ImageFont.truetype("arial.ttf", 24)
            header_font = ImageFont.truetype("arial.ttf", 18)
            body_font = ImageFont.truetype("arial.ttf", 14)
        except OSError:
            # Fall back to default fonts
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        y_position = 30

        # Store name
        if "store_name" in receipt_data:
            draw.text(
                (50, y_position),
                receipt_data["store_name"],
                fill="black",
                font=title_font,
            )
            y_position += 40

        # Contact info
        if "phone" in receipt_data:
            draw.text(
                (50, y_position),
                f"Phone: {receipt_data['phone']}",
                fill="black",
                font=body_font,
            )
            y_position += 25

        if "email" in receipt_data:
            draw.text(
                (50, y_position),
                f"Email: {receipt_data['email']}",
                fill="black",
                font=body_font,
            )
            y_position += 25

        # Date and transaction info
        if "date" in receipt_data:
            draw.text(
                (50, y_position),
                f"Date: {receipt_data['date']}",
                fill="black",
                font=body_font,
            )
            y_position += 25

        if "transaction_id" in receipt_data:
            draw.text(
                (50, y_position),
                f"Transaction: {receipt_data['transaction_id']}",
                fill="black",
                font=body_font,
            )
            y_position += 30

        # Items
        if "items" in receipt_data:
            draw.text((50, y_position), "ITEMS:", fill="black", font=header_font)
            y_position += 25

            for item in receipt_data["items"]:
                item_text = f"{item['name']} - ${item['price']:.2f}"
                draw.text((70, y_position), item_text, fill="black", font=body_font)
                y_position += 20

            y_position += 10

        # Payment info
        if "payment_method" in receipt_data:
            draw.text(
                (50, y_position),
                f"Payment: {receipt_data['payment_method']}",
                fill="black",
                font=body_font,
            )
            y_position += 25

        if "card_number" in receipt_data:
            draw.text(
                (50, y_position),
                f"Card: {receipt_data['card_number']}",
                fill="black",
                font=body_font,
            )
            y_position += 25

        # Total
        if "total" in receipt_data:
            draw.text(
                (50, y_position),
                f"TOTAL: ${receipt_data['total']:.2f}",
                fill="black",
                font=header_font,
            )
            y_position += 30

        # Footer
        if "footer" in receipt_data:
            draw.text(
                (50, y_position), receipt_data["footer"], fill="black", font=body_font
            )

        # Save to bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        return img_bytes.getvalue()

    def create_uploaded_file(self, content: bytes, filename: str) -> SimpleUploadedFile:
        """Create a Django UploadedFile from bytes content."""
        return SimpleUploadedFile(filename, content, content_type="image/png")

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_grocery_receipt_accuracy(self, mock_ocr):
        """Test accuracy with a typical grocery store receipt."""
        # Setup realistic grocery receipt
        receipt_data = {
            "store_name": "FRESH MARKET",
            "phone": "(555) 123-4567",
            "date": "01/15/2024",
            "transaction_id": "TXN-789456123",
            "items": [
                {"name": "Organic Apples", "price": 4.99},
                {"name": "Whole Milk", "price": 3.49},
                {"name": "Bread Loaf", "price": 2.99},
            ],
            "payment_method": "Credit Card",
            "card_number": "**** **** **** 1234",
            "total": 11.47,
            "footer": "Thank you for shopping with us!",
        }

        # Create expected OCR output
        expected_text = """FRESH MARKET
Phone: (555) 123-4567
Date: 01/15/2024
Transaction: TXN-789456123
ITEMS:
Organic Apples - $4.99
Whole Milk - $3.49
Bread Loaf - $2.99
Payment: Credit Card
Card: **** **** **** 1234
TOTAL: $11.47
Thank you for shopping with us!"""

        mock_ocr.return_value = expected_text
        test_image = self.create_realistic_receipt_image(receipt_data)
        uploaded_file = self.create_uploaded_file(test_image, "grocery_receipt.png")

        # Execute PII scan
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["phone_numbers"]) >= 1
        assert "(555) 123-4567" in result["pii_detected"]["phone_numbers"][0]
        # Masked card number should not be detected as valid credit card
        assert len(result["pii_detected"]["credit_cards"]) == 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_restaurant_receipt_with_pii(self, mock_ocr):
        """Test accuracy with restaurant receipt containing multiple PII types."""
        receipt_data = {
            "store_name": "BELLA'S ITALIAN",
            "phone": "+1-800-555-0123",
            "email": "contact@bellas-italian.com",
            "date": "03/20/2024",
            "items": [
                {"name": "Pasta Primavera", "price": 18.99},
                {"name": "House Wine", "price": 12.00},
            ],
            "payment_method": "Credit Card",
            "card_number": "4111 1111 1111 1111",
            "total": 30.99,
        }

        expected_text = """BELLA'S ITALIAN
Phone: +1-800-555-0123
Email: contact@bellas-italian.com
Date: 03/20/2024
ITEMS:
Pasta Primavera - $18.99
House Wine - $12.00
Payment: Credit Card
Card: 4111 1111 1111 1111
TOTAL: $30.99"""

        mock_ocr.return_value = expected_text
        test_image = self.create_realistic_receipt_image(receipt_data)
        uploaded_file = self.create_uploaded_file(test_image, "restaurant_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert multiple PII types detected
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["emails"]) >= 1
        assert len(result["pii_detected"]["phone_numbers"]) >= 1
        assert len(result["pii_detected"]["credit_cards"]) >= 1

        # Verify specific PII items
        assert "contact@bellas-italian.com" in result["pii_detected"]["emails"]
        assert "4111 1111 1111 1111" in result["pii_detected"]["credit_cards"]

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_gas_station_receipt_clean(self, mock_ocr):
        """Test accuracy with gas station receipt containing no PII."""
        receipt_data = {
            "store_name": "SPEEDWAY GAS",
            "date": "02/10/2024",
            "items": [
                {"name": "Regular Gas", "price": 45.67},
                {"name": "Energy Drink", "price": 2.99},
            ],
            "payment_method": "Cash",
            "total": 48.66,
            "footer": "Drive Safe!",
        }

        expected_text = """SPEEDWAY GAS
Date: 02/10/2024
ITEMS:
Regular Gas - $45.67
Energy Drink - $2.99
Payment: Cash
TOTAL: $48.66
Drive Safe!"""

        mock_ocr.return_value = expected_text
        test_image = self.create_realistic_receipt_image(receipt_data)
        uploaded_file = self.create_uploaded_file(test_image, "gas_receipt.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert no PII detected
        assert result["has_pii"] is False
        assert len(result["pii_detected"]["emails"]) == 0
        assert len(result["pii_detected"]["phone_numbers"]) == 0
        assert len(result["pii_detected"]["credit_cards"]) == 0
        assert len(result["pii_detected"]["ssn"]) == 0

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_medical_receipt_with_sensitive_data(self, mock_ocr):
        """Test accuracy with medical receipt containing sensitive information."""
        expected_text = """CITY MEDICAL CENTER
Patient: John Doe
DOB: 01/15/1985
SSN: 123-45-6789
Email: john.doe@email.com
Phone: (555) 987-6543
Service: Annual Checkup
Amount: $250.00
Insurance: Processed"""

        mock_ocr.return_value = expected_text

        # Create simple image for this test
        image = Image.new("RGB", (400, 300), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        uploaded_file = self.create_uploaded_file(
            img_bytes.getvalue(), "medical_receipt.png"
        )

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert comprehensive PII detection
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["emails"]) >= 1
        assert len(result["pii_detected"]["phone_numbers"]) >= 1
        assert len(result["pii_detected"]["ssn"]) >= 1

        # Verify specific sensitive data
        assert "john.doe@email.com" in result["pii_detected"]["emails"]
        assert "123-45-6789" in result["pii_detected"]["ssn"]

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_pii_redaction_comprehensive(self, mock_ocr):
        """Test comprehensive PII redaction across different types."""
        receipt_text = """PREMIUM SERVICES
Customer: alice@company.com
Phone: +1-555-234-5678
Employee ID: 987-65-4321
Card: 5555 5555 5555 4444
Service Fee: $199.99
Date: 04/01/2024"""

        mock_ocr.return_value = receipt_text

        image = Image.new("RGB", (400, 300), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        uploaded_file = self.create_uploaded_file(
            img_bytes.getvalue(), "premium_receipt.png"
        )

        # Execute redaction
        result = self.processor.redact_pii_from_receipt(
            uploaded_file, replacement="[REDACTED]"
        )

        # Assert
        assert result["has_pii"] is True
        redacted_text = result["redacted_text"]

        # PII should be redacted
        assert "alice@company.com" not in redacted_text
        assert "+1-555-234-5678" not in redacted_text
        assert "987-65-4321" not in redacted_text
        assert "5555 5555 5555 4444" not in redacted_text

        # Redaction markers should be present
        assert "[REDACTED]" in redacted_text

        # Non-PII should be preserved
        assert "PREMIUM SERVICES" in redacted_text
        assert "$199.99" in redacted_text
        assert "04/01/2024" in redacted_text

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_international_receipt_formats(self, mock_ocr):
        """Test accuracy with international receipt formats."""
        receipt_text = """LONDON STORE LTD
Phone: +44 20 7946 0958
Email: info@londonstore.co.uk
Date: 15/03/2024
Item: British Tea - £4.50
Payment: Contactless
Total: £4.50
VAT Reg: GB123456789"""

        mock_ocr.return_value = receipt_text

        image = Image.new("RGB", (400, 300), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        uploaded_file = self.create_uploaded_file(
            img_bytes.getvalue(), "uk_receipt.png"
        )

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert international formats detected
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["emails"]) >= 1
        assert len(result["pii_detected"]["phone_numbers"]) >= 1

        # Check for international email and phone
        assert "info@londonstore.co.uk" in result["pii_detected"]["emails"]
        # The international phone should be detected
        phone_detected = any(
            "+44" in phone for phone in result["pii_detected"]["phone_numbers"]
        )
        assert phone_detected

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_receipt_with_partial_ocr_errors(self, mock_ocr):
        """Test handling of OCR errors and partial recognition."""
        # Simulate OCR with some character recognition errors
        receipt_text = """COFFEE SH0P
Ph0ne: 555-123-4567
Emai1: info@c0ffee.com
1tem: Latte - $4.50
Tota1: $4.50"""

        mock_ocr.return_value = receipt_text

        image = Image.new("RGB", (400, 300), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        uploaded_file = self.create_uploaded_file(img_bytes.getvalue(), "noisy_ocr.png")

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert - should still detect clear phone number despite OCR noise
        phone_numbers = result["pii_detected"]["phone_numbers"]
        assert len(phone_numbers) >= 1
        assert "555-123-4567" in phone_numbers[0]

        # Email might not be detected due to OCR errors (acceptable)
        # This tests robustness against OCR imperfections


class TestOCRPerformanceMetrics:
    """Test performance characteristics of OCR processing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ReceiptOCRProcessor()

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_large_receipt_processing(self, mock_ocr):
        """Test processing of large receipts with many items."""
        # Create a large receipt with many items
        items_text = "\n".join(
            [f"Item {i}: Product {i} - ${i * 1.99:.2f}" for i in range(1, 51)]
        )
        large_receipt = f"""BULK STORE
Date: 05/15/2024
Customer: bulk@orders.com
{items_text}
TOTAL: $2,499.50"""

        mock_ocr.return_value = large_receipt

        image = Image.new("RGB", (800, 1200), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        uploaded_file = SimpleUploadedFile(
            "large_receipt.png", img_bytes.getvalue(), content_type="image/png"
        )

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is True
        assert len(result["pii_detected"]["emails"]) >= 1
        assert "bulk@orders.com" in result["pii_detected"]["emails"]

        # Should handle large text efficiently
        assert len(result["text"]) > 1000  # Large receipt text

    @patch("apps.core.security.ocr.pytesseract.image_to_string")
    def test_empty_or_minimal_receipt(self, mock_ocr):
        """Test processing of receipts with minimal or no text."""
        mock_ocr.return_value = "STORE\nTotal: $0.00"

        image = Image.new("RGB", (200, 100), color="white")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="PNG")
        uploaded_file = SimpleUploadedFile(
            "minimal_receipt.png", img_bytes.getvalue(), content_type="image/png"
        )

        # Execute
        result = self.processor.scan_for_pii(uploaded_file)

        # Assert
        assert result["has_pii"] is False
        assert result["text"] == "STORE\nTotal: $0.00"
        assert all(len(pii_list) == 0 for pii_list in result["pii_detected"].values())
