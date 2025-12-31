"""Tests for hybrid pipeline configuration classes."""

import pytest

from opendataloader_pdf.hybrid import (
    AIModelConfig,
    FormulaConfig,
    HybridPipelineConfig,
    LayoutConfig,
    OCRConfig,
    PictureConfig,
    TableConfig,
    TriageConfig,
)


class TestTriageConfig:
    """Tests for TriageConfig."""

    def test_default_values(self):
        """Test default threshold values match Java Config."""
        config = TriageConfig()
        assert config.image_area_threshold == 0.05
        assert config.text_coverage_threshold == 0.10
        assert config.missing_to_unicode_threshold == 0.30

    def test_custom_values(self):
        """Test custom threshold values."""
        config = TriageConfig(
            image_area_threshold=0.15,
            text_coverage_threshold=0.05,
            missing_to_unicode_threshold=0.50,
        )
        assert config.image_area_threshold == 0.15
        assert config.text_coverage_threshold == 0.05
        assert config.missing_to_unicode_threshold == 0.50


class TestOCRConfig:
    """Tests for OCRConfig."""

    def test_default_values(self):
        """Test OCR is enabled by default with RapidOCR."""
        config = OCRConfig()
        assert config.enabled is True
        assert config.engine == "rapidocr"
        assert config.language == "en"
        assert config.languages is None

    def test_tesseract_engine(self):
        """Test Tesseract configuration."""
        config = OCRConfig(engine="tesseract", language="ko", languages=["en", "ja"])
        assert config.engine == "tesseract"
        assert config.language == "ko"
        assert config.languages == ["en", "ja"]


class TestTableConfig:
    """Tests for TableConfig."""

    def test_default_values(self):
        """Test table detection is enabled by default."""
        config = TableConfig()
        assert config.enabled is True
        assert config.model == "docling"
        assert config.min_confidence == 0.5


class TestLayoutConfig:
    """Tests for LayoutConfig."""

    def test_default_values(self):
        """Test layout analysis is enabled by default."""
        config = LayoutConfig()
        assert config.enabled is True
        assert config.model == "docling"


class TestFormulaConfig:
    """Tests for FormulaConfig."""

    def test_default_disabled(self):
        """Test formula detection is disabled by default."""
        config = FormulaConfig()
        assert config.enabled is False

    def test_can_enable(self):
        """Test formula detection can be enabled."""
        config = FormulaConfig(enabled=True)
        assert config.enabled is True


class TestPictureConfig:
    """Tests for PictureConfig."""

    def test_default_disabled(self):
        """Test picture classification is disabled by default."""
        config = PictureConfig()
        assert config.enabled is False

    def test_can_enable(self):
        """Test picture classification can be enabled."""
        config = PictureConfig(enabled=True)
        assert config.enabled is True


class TestAIModelConfig:
    """Tests for AIModelConfig."""

    def test_default_models_enabled(self):
        """Test default model configuration."""
        config = AIModelConfig()
        assert config.ocr.enabled is True
        assert config.table.enabled is True
        assert config.layout.enabled is True
        assert config.formula.enabled is False
        assert config.picture.enabled is False

    def test_custom_model_config(self):
        """Test custom model configuration."""
        config = AIModelConfig(
            ocr=OCRConfig(enabled=False),
            formula=FormulaConfig(enabled=True),
        )
        assert config.ocr.enabled is False
        assert config.formula.enabled is True
        # Defaults remain for unspecified
        assert config.table.enabled is True


class TestHybridPipelineConfig:
    """Tests for HybridPipelineConfig."""

    def test_default_values(self):
        """Test default pipeline configuration."""
        config = HybridPipelineConfig()
        assert config.batch_size == 4
        assert config.temp_dir is None
        assert config.keep_intermediate is False
        # Check nested defaults
        assert config.triage.image_area_threshold == 0.05
        assert config.ai_models.ocr.enabled is True

    def test_fast_mode_preset(self):
        """Test fast_mode preset configuration."""
        config = HybridPipelineConfig.fast_mode()
        # Higher thresholds for more fast-path routing
        assert config.triage.image_area_threshold == 0.15
        assert config.triage.text_coverage_threshold == 0.05
        # Table and layout disabled for speed
        assert config.ai_models.table.enabled is False
        assert config.ai_models.layout.enabled is False
        # Larger batch size
        assert config.batch_size == 8

    def test_quality_mode_preset(self):
        """Test quality_mode preset configuration."""
        config = HybridPipelineConfig.quality_mode()
        # Lower thresholds for more AI processing
        assert config.triage.image_area_threshold == 0.02
        assert config.triage.text_coverage_threshold == 0.15
        # All models enabled
        assert config.ai_models.ocr.enabled is True
        assert config.ai_models.table.enabled is True
        assert config.ai_models.layout.enabled is True
        assert config.ai_models.formula.enabled is True
        assert config.ai_models.picture.enabled is True
        # Smaller batch size for quality
        assert config.batch_size == 2

    def test_custom_config(self):
        """Test fully custom configuration."""
        config = HybridPipelineConfig(
            triage=TriageConfig(image_area_threshold=0.10),
            ai_models=AIModelConfig(
                ocr=OCRConfig(engine="tesseract"),
            ),
            batch_size=2,
            keep_intermediate=True,
        )
        assert config.triage.image_area_threshold == 0.10
        assert config.ai_models.ocr.engine == "tesseract"
        assert config.batch_size == 2
        assert config.keep_intermediate is True
