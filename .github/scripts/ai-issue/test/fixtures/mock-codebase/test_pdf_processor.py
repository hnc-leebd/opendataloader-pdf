"""Tests for pdf_processor module."""
import pytest
from pdf_processor import process_pdf, load_pages


def test_process_pdf_with_no_pages():
    """Test that processing a PDF with no pages returns an empty list.

    This test verifies the fix for issue #15:
    PDFs with no pages should return an empty result instead of raising TypeError
    """
    result = process_pdf("empty.pdf")
    assert result == []


def test_load_pages_returns_none():
    """Test that load_pages returns None for empty PDFs."""
    result = load_pages("empty.pdf")
    assert result is None


def test_process_pdf_with_skip_empty_no_pages():
    """Test that processing a PDF with no pages and skip_empty=True returns empty list."""
    result = process_pdf("empty.pdf", skip_empty=True)
    assert result == []


def test_process_pdf_with_invalid_path():
    """Test that processing with invalid file path raises ValueError."""
    with pytest.raises(ValueError, match="Invalid PDF format"):
        process_pdf("")
