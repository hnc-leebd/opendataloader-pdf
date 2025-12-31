"""Tests for model adapters."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from opendataloader_pdf.hybrid.config import LayoutConfig, OCRConfig, TableConfig
from opendataloader_pdf.hybrid.models import ModelRegistry
from opendataloader_pdf.hybrid.models.base import BaseModelAdapter


class MockAdapter(BaseModelAdapter):
    """Mock adapter for testing base class."""

    def _load_model(self):
        self._model = MagicMock()

    def process(self, image_path, page_number):
        return {"elements": [], "source": "mock"}


class TestModelRegistry:
    """Tests for ModelRegistry singleton pattern."""

    def setup_method(self):
        """Clear registry before each test."""
        ModelRegistry.clear()

    def test_get_creates_instance(self):
        """Test registry creates new instance on first get."""
        adapter = ModelRegistry.get(MockAdapter)
        assert adapter is not None
        assert isinstance(adapter, MockAdapter)

    def test_get_returns_same_instance(self):
        """Test registry returns same instance on subsequent gets."""
        adapter1 = ModelRegistry.get(MockAdapter)
        adapter2 = ModelRegistry.get(MockAdapter)
        assert adapter1 is adapter2

    def test_clear_removes_instances(self):
        """Test clear removes all cached instances."""
        adapter1 = ModelRegistry.get(MockAdapter)
        ModelRegistry.clear()
        adapter2 = ModelRegistry.get(MockAdapter)
        assert adapter1 is not adapter2


class TestBaseModelAdapter:
    """Tests for BaseModelAdapter."""

    def test_is_loaded_initially_false(self):
        """Test model is not loaded initially."""
        adapter = MockAdapter()
        assert adapter.is_loaded is False

    def test_ensure_loaded_loads_model(self):
        """Test ensure_loaded triggers model loading."""
        adapter = MockAdapter()
        adapter.ensure_loaded()
        assert adapter.is_loaded is True

    def test_cleanup_unloads_model(self):
        """Test cleanup unloads the model."""
        adapter = MockAdapter()
        adapter.ensure_loaded()
        adapter.cleanup()
        assert adapter.is_loaded is False


class TestOCRAdapter:
    """Tests for OCRAdapter."""

    @pytest.fixture
    def mock_image(self):
        """Create a mock image file."""
        pytest.importorskip("PIL")
        from PIL import Image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Create a minimal valid PNG
            img = Image.new("RGB", (100, 100), color="white")
            img.save(f.name)
            yield Path(f.name)

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        from opendataloader_pdf.hybrid.models.ocr import OCRAdapter
        adapter = OCRAdapter()
        assert adapter.config.enabled is True
        assert adapter.config.engine == "rapidocr"

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        from opendataloader_pdf.hybrid.models.ocr import OCRAdapter
        config = OCRConfig(engine="tesseract", language="ko")
        adapter = OCRAdapter(config=config)
        assert adapter.config.engine == "tesseract"
        assert adapter.config.language == "ko"

    @patch("opendataloader_pdf.hybrid.models.ocr.OCRAdapter._load_rapidocr")
    def test_process_returns_schema_format(self, mock_load, mock_image):
        """Test process returns elements in JSON schema format."""
        from opendataloader_pdf.hybrid.models.ocr import OCRAdapter

        adapter = OCRAdapter()
        adapter._model = MagicMock()
        adapter._model.return_value = (
            [
                ([[0, 0], [100, 0], [100, 20], [0, 20]], "Test text", 0.95),
            ],
            None,
        )

        result = adapter.process(mock_image, 0)

        assert "elements" in result
        assert result["source"] == "ocr"
        assert len(result["elements"]) == 1
        elem = result["elements"][0]
        assert elem["type"] == "paragraph"
        assert elem["page number"] == 1  # 1-indexed
        assert "bounding box" in elem
        assert elem["content"] == "Test text"


class TestTableAdapter:
    """Tests for TableAdapter."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        from opendataloader_pdf.hybrid.models.table import TableAdapter
        adapter = TableAdapter()
        assert adapter.config.enabled is True
        assert adapter.config.model == "docling"

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        from opendataloader_pdf.hybrid.models.table import TableAdapter
        config = TableConfig(min_confidence=0.7)
        adapter = TableAdapter(config=config)
        assert adapter.config.min_confidence == 0.7


class TestLayoutAdapter:
    """Tests for LayoutAdapter."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        from opendataloader_pdf.hybrid.models.layout import LayoutAdapter
        adapter = LayoutAdapter()
        assert adapter.config.enabled is True
        assert adapter.config.model == "docling"

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        from opendataloader_pdf.hybrid.models.layout import LayoutAdapter
        config = LayoutConfig(model="custom")
        adapter = LayoutAdapter(config=config)
        assert adapter.config.model == "custom"

    def test_get_region_type_mapping(self):
        """Test region type mapping to JSON schema types."""
        from opendataloader_pdf.hybrid.models.layout import LayoutAdapter
        adapter = LayoutAdapter()

        # Create mock regions with different types
        mock_region = MagicMock()

        type_tests = [
            ("text", "paragraph"),
            ("paragraph", "paragraph"),
            ("title", "heading"),
            ("heading", "heading"),
            ("caption", "caption"),
            ("figure", "image"),
            ("table", "table"),
            ("list", "list"),
            ("list_item", "list item"),
        ]

        for raw_type, expected in type_tests:
            mock_region.type = raw_type
            result = adapter._get_region_type(mock_region)
            assert result == expected, f"Expected {expected} for {raw_type}, got {result}"
