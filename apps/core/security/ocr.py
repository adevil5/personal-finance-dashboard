"""
OCR (Optical Character Recognition) functionality for receipt processing.

This module provides OCR capabilities to extract text from uploaded receipt images
and integrates with PII detection to identify and redact sensitive information.
"""

import logging
from typing import Dict, List, Optional, Union

try:
    import pytesseract
    from PIL import Image

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from django.core.files.uploadedfile import UploadedFile

from .pii_detection import PIIDetector

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """Custom exception for OCR-related errors."""

    pass


class ReceiptOCRProcessor:
    """
    Processes receipt images using OCR to extract text and detect PII.

    This class integrates pytesseract for OCR functionality with our existing
    PII detection system to scan uploaded receipts for sensitive information.
    """

    def __init__(self, tesseract_config: Optional[str] = None):
        """
        Initialize the OCR processor.

        Args:
            tesseract_config: Optional tesseract configuration string
        """
        if not TESSERACT_AVAILABLE:
            raise OCRError(
                "OCR functionality requires pytesseract and PIL. "
                "Please install with: pip install pytesseract pillow"
            )

        self.tesseract_config = tesseract_config or "--psm 6"  # Default config
        self.pii_detector = PIIDetector()

        # Supported image formats
        self.supported_formats = ["PNG", "JPEG", "JPG", "GIF", "BMP", "TIFF"]

    def extract_text_from_image(
        self, uploaded_file: UploadedFile, min_confidence: Optional[int] = None
    ) -> str:
        """
        Extract text from an uploaded image file using OCR.

        Args:
            uploaded_file: Django UploadedFile containing image data
            min_confidence: Minimum confidence threshold for text recognition

        Returns:
            Extracted text as string

        Raises:
            OCRError: If OCR processing fails or file is invalid
        """
        if not uploaded_file:
            raise OCRError("No file provided for OCR processing")

        try:
            # Reset file pointer to beginning
            uploaded_file.seek(0)

            # Load image using PIL
            image = Image.open(uploaded_file)

            # Convert to RGB if necessary (for better OCR results)
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Perform OCR with tesseract
            if min_confidence is not None:
                # Use image_to_data for confidence-based filtering
                ocr_data = pytesseract.image_to_data(
                    image,
                    config=self.tesseract_config,
                    output_type=pytesseract.Output.DICT,
                )

                # Filter text by confidence
                text_parts = []
                for i, conf in enumerate(ocr_data["conf"]):
                    if int(conf) >= min_confidence:
                        text = ocr_data["text"][i].strip()
                        if text:
                            text_parts.append(text)

                extracted_text = " ".join(text_parts)
            else:
                # Standard text extraction
                extracted_text = pytesseract.image_to_string(
                    image, config=self.tesseract_config
                )

            # Clean up the extracted text
            extracted_text = self._clean_extracted_text(extracted_text)

            logger.debug(f"OCR extracted {len(extracted_text)} characters from image")
            return extracted_text

        except Exception as e:
            if "tesseract" in str(e).lower() or "tess" in str(e).lower():
                logger.error(f"Tesseract OCR error: {e}")
                raise OCRError(f"Failed to extract text from image: {str(e)}")
            elif "cannot identify image file" in str(e).lower():
                logger.error(f"Invalid image file: {e}")
                raise OCRError("Failed to process image file: Invalid image format")
            else:
                logger.error(f"Unexpected OCR error: {e}")
                raise OCRError(f"Failed to extract text from image: {str(e)}")
        finally:
            # Reset file pointer
            try:
                uploaded_file.seek(0)
            except (AttributeError, ValueError):
                pass

    def scan_for_pii(
        self, uploaded_file: UploadedFile
    ) -> Dict[str, Union[bool, str, Dict]]:
        """
        Extract text from image and scan for PII.

        Args:
            uploaded_file: Django UploadedFile containing image data

        Returns:
            Dictionary containing:
            - has_pii: Boolean indicating if PII was found
            - text: Extracted text from image
            - pii_detected: Dictionary of detected PII by type

        Raises:
            OCRError: If OCR processing fails
        """
        try:
            # Extract text using OCR
            extracted_text = self.extract_text_from_image(uploaded_file)

            # Scan for PII using existing detector
            pii_results = self.pii_detector.detect_all(extracted_text)
            has_pii = self.pii_detector.has_pii(extracted_text)

            result = {
                "has_pii": has_pii,
                "text": extracted_text,
                "pii_detected": pii_results,
            }

            logger.info(
                f"PII scan completed. Has PII: {has_pii}, "
                f"Text length: {len(extracted_text)}"
            )

            return result

        except OCRError:
            raise
        except Exception as e:
            logger.error(f"Error during PII scanning: {e}")
            raise OCRError(f"Failed to scan image for PII: {str(e)}")

    def redact_pii_from_receipt(
        self, uploaded_file: UploadedFile, replacement: str = "[PII_REDACTED]"
    ) -> Dict[str, Union[bool, str, Dict]]:
        """
        Extract text from receipt image and redact any detected PII.

        Args:
            uploaded_file: Django UploadedFile containing image data
            replacement: String to replace PII with

        Returns:
            Dictionary containing:
            - has_pii: Boolean indicating if PII was found
            - original_text: Original extracted text
            - redacted_text: Text with PII redacted
            - pii_detected: Dictionary of detected PII by type

        Raises:
            OCRError: If OCR processing fails
        """
        try:
            # First scan for PII
            scan_result = self.scan_for_pii(uploaded_file)

            original_text = scan_result["text"]
            pii_detected = scan_result["pii_detected"]
            has_pii = scan_result["has_pii"]

            # Redact PII if found
            if has_pii:
                redacted_text = self.pii_detector.sanitize_for_logging(
                    original_text, replacement=replacement
                )
            else:
                redacted_text = original_text

            result = {
                "has_pii": has_pii,
                "original_text": original_text,
                "redacted_text": redacted_text,
                "pii_detected": pii_detected,
            }

            logger.info(
                f"PII redaction completed. Had PII: {has_pii}, "
                f"Original length: {len(original_text)}, "
                f"Redacted length: {len(redacted_text)}"
            )

            return result

        except OCRError:
            raise
        except Exception as e:
            logger.error(f"Error during PII redaction: {e}")
            raise OCRError(f"Failed to redact PII from receipt: {str(e)}")

    def get_text_with_positions(
        self, uploaded_file: UploadedFile
    ) -> Dict[str, List[Dict]]:
        """
        Extract text with position information for advanced processing.

        Args:
            uploaded_file: Django UploadedFile containing image data

        Returns:
            Dictionary with detailed OCR data including positions

        Raises:
            OCRError: If OCR processing fails
        """
        if not uploaded_file:
            raise OCRError("No file provided for OCR processing")

        try:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)

            if image.mode != "RGB":
                image = image.convert("RGB")

            # Get detailed OCR data with positions
            ocr_data = pytesseract.image_to_data(
                image, config=self.tesseract_config, output_type=pytesseract.Output.DICT
            )

            # Structure the data for easier use
            text_elements = []
            for i in range(len(ocr_data["text"])):
                text = ocr_data["text"][i].strip()
                if text:  # Only include non-empty text
                    element = {
                        "text": text,
                        "confidence": int(ocr_data["conf"][i]),
                        "left": int(ocr_data["left"][i]),
                        "top": int(ocr_data["top"][i]),
                        "width": int(ocr_data["width"][i]),
                        "height": int(ocr_data["height"][i]),
                        "level": int(ocr_data["level"][i]),
                        "page_num": int(ocr_data["page_num"][i]),
                        "block_num": int(ocr_data["block_num"][i]),
                        "par_num": int(ocr_data["par_num"][i]),
                        "line_num": int(ocr_data["line_num"][i]),
                        "word_num": int(ocr_data["word_num"][i]),
                    }
                    text_elements.append(element)

            return {
                "text_elements": text_elements,
                "total_elements": len(text_elements),
            }

        except Exception as e:
            logger.error(f"Error extracting text with positions: {e}")
            raise OCRError(f"Failed to extract positioned text: {str(e)}")
        finally:
            try:
                uploaded_file.seek(0)
            except (AttributeError, ValueError):
                pass

    def _clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted OCR text.

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace and normalize line breaks
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Strip whitespace and remove empty lines
            cleaned_line = line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        # Join lines with single newlines
        cleaned_text = "\n".join(cleaned_lines)

        # Remove multiple consecutive spaces
        import re

        cleaned_text = re.sub(r" +", " ", cleaned_text)

        return cleaned_text

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported image formats.

        Returns:
            List of supported format names
        """
        return self.supported_formats.copy()

    def validate_image_format(self, uploaded_file: UploadedFile) -> bool:
        """
        Validate that uploaded file is a supported image format.

        Args:
            uploaded_file: Django UploadedFile to validate

        Returns:
            True if format is supported, False otherwise
        """
        if not uploaded_file or not uploaded_file.name:
            return False

        try:
            # Check file extension
            file_ext = uploaded_file.name.split(".")[-1].upper()
            if file_ext not in self.supported_formats:
                return False

            # Try to open with PIL to verify it's actually an image
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
            image.verify()  # Verify it's a valid image
            uploaded_file.seek(0)

            return True

        except Exception:
            return False
        finally:
            try:
                uploaded_file.seek(0)
            except (AttributeError, ValueError):
                pass

    def preprocess_image_for_ocr(self, uploaded_file: UploadedFile) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.

        Args:
            uploaded_file: Django UploadedFile containing image data

        Returns:
            Preprocessed PIL Image

        Raises:
            OCRError: If image processing fails
        """
        try:
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Basic preprocessing for better OCR
            # You could add more sophisticated preprocessing here:
            # - Noise reduction
            # - Contrast enhancement
            # - Rotation correction
            # - Deskewing

            return image

        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            raise OCRError(f"Failed to preprocess image: {str(e)}")
        finally:
            try:
                uploaded_file.seek(0)
            except (AttributeError, ValueError):
                pass


# Convenience functions for common operations


def extract_text_from_receipt(uploaded_file: UploadedFile) -> str:
    """
    Convenience function to extract text from a receipt image.

    Args:
        uploaded_file: Django UploadedFile containing image data

    Returns:
        Extracted text as string

    Raises:
        OCRError: If OCR processing fails
    """
    processor = ReceiptOCRProcessor()
    return processor.extract_text_from_image(uploaded_file)


def scan_receipt_for_pii(
    uploaded_file: UploadedFile,
) -> Dict[str, Union[bool, str, Dict]]:
    """
    Convenience function to scan a receipt for PII.

    Args:
        uploaded_file: Django UploadedFile containing image data

    Returns:
        Dictionary with PII scan results

    Raises:
        OCRError: If OCR processing fails
    """
    processor = ReceiptOCRProcessor()
    return processor.scan_for_pii(uploaded_file)


def redact_pii_from_receipt_image(
    uploaded_file: UploadedFile, replacement: str = "[PII_REDACTED]"
) -> Dict[str, Union[bool, str, Dict]]:
    """
    Convenience function to redact PII from a receipt image.

    Args:
        uploaded_file: Django UploadedFile containing image data
        replacement: String to replace PII with

    Returns:
        Dictionary with redaction results

    Raises:
        OCRError: If OCR processing fails
    """
    processor = ReceiptOCRProcessor()
    return processor.redact_pii_from_receipt(uploaded_file, replacement)
