"""Tests for OCR module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile


def test_is_scanned_pdf_text_pdf():
    """Text PDFs should return False."""
    from src.ocr import is_scanned_pdf

    with patch('src.ocr.extract_text_from_pdf') as mock_extract:
        mock_extract.return_value = "This is some text content from the PDF"
        result = is_scanned_pdf(Path("/fake/path.pdf"))
        assert result is False


def test_is_scanned_pdf_image_pdf():
    """Scanned PDFs (no text) should return True."""
    from src.ocr import is_scanned_pdf

    with patch('src.ocr.extract_text_from_pdf') as mock_extract:
        mock_extract.return_value = ""
        result = is_scanned_pdf(Path("/fake/path.pdf"))
        assert result is True


def test_is_supported_image():
    """Test image format detection."""
    from src.ocr import is_supported_image

    assert is_supported_image(Path("receipt.jpg")) is True
    assert is_supported_image(Path("receipt.jpeg")) is True
    assert is_supported_image(Path("receipt.png")) is True
    assert is_supported_image(Path("receipt.heic")) is True
    assert is_supported_image(Path("document.pdf")) is False
    assert is_supported_image(Path("file.txt")) is False


def test_validate_image_size():
    """Test image size validation."""
    from src.ocr import validate_image_size

    with patch('pathlib.Path.stat') as mock_stat:
        mock_stat.return_value.st_size = 5 * 1024 * 1024  # 5MB
        result, error = validate_image_size(Path("/fake/image.jpg"))
        assert result is True

        mock_stat.return_value.st_size = 15 * 1024 * 1024  # 15MB
        result, error = validate_image_size(Path("/fake/image.jpg"))
        assert result is False
        assert "10MB" in error
