"""
Configuration classes for the hybrid pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TriageConfig:
    """Configuration for page triage thresholds.

    These thresholds match the Java Config defaults and determine
    when a page is routed to AI processing.
    """

    image_area_threshold: float = 0.05
    """Pages with image area ratio above this (default 5%) need OCR."""

    text_coverage_threshold: float = 0.10
    """Pages with text coverage below this (default 10%) need OCR."""

    missing_to_unicode_threshold: float = 0.30
    """Pages with missing ToUnicode ratio above this (default 30%) need OCR."""


@dataclass
class OCRConfig:
    """Configuration for OCR model."""

    enabled: bool = True
    """Whether OCR processing is enabled."""

    engine: str = "rapidocr"
    """OCR engine to use: 'rapidocr' or 'tesseract'."""

    language: str = "en"
    """Primary language for OCR."""

    languages: Optional[list[str]] = None
    """Additional languages for multi-language OCR."""


@dataclass
class TableConfig:
    """Configuration for table detection model."""

    enabled: bool = True
    """Whether table detection is enabled."""

    model: str = "docling"
    """Table detection model: 'docling' (TableFormer)."""

    min_confidence: float = 0.5
    """Minimum confidence threshold for table detection."""


@dataclass
class LayoutConfig:
    """Configuration for layout analysis model."""

    enabled: bool = True
    """Whether layout analysis is enabled."""

    model: str = "docling"
    """Layout model to use."""


@dataclass
class FormulaConfig:
    """Configuration for formula/equation detection model."""

    enabled: bool = False
    """Whether formula detection is enabled (disabled by default)."""

    model: str = "docling"
    """Formula detection model to use."""


@dataclass
class PictureConfig:
    """Configuration for picture classification model."""

    enabled: bool = False
    """Whether picture classification is enabled (disabled by default)."""

    model: str = "docling"
    """Picture classification model to use."""


@dataclass
class AIModelConfig:
    """Configuration for AI models used in hybrid processing.

    By default, OCR, Table, and Layout models are enabled.
    Formula and Picture models are disabled but can be enabled by users.
    """

    ocr: OCRConfig = field(default_factory=OCRConfig)
    """OCR model configuration (enabled by default)."""

    table: TableConfig = field(default_factory=TableConfig)
    """Table detection configuration (enabled by default)."""

    layout: LayoutConfig = field(default_factory=LayoutConfig)
    """Layout analysis configuration (enabled by default)."""

    formula: FormulaConfig = field(default_factory=FormulaConfig)
    """Formula detection configuration (disabled by default)."""

    picture: PictureConfig = field(default_factory=PictureConfig)
    """Picture classification configuration (disabled by default)."""


@dataclass
class HybridPipelineConfig:
    """Main configuration for the hybrid processing pipeline.

    The hybrid pipeline combines fast JAR extraction for simple pages
    with AI model processing for complex pages (scanned, tables, etc.).
    """

    triage: TriageConfig = field(default_factory=TriageConfig)
    """Page triage configuration."""

    ai_models: AIModelConfig = field(default_factory=AIModelConfig)
    """AI model configuration."""

    batch_size: int = 4
    """Number of pages to process in parallel with AI models."""

    temp_dir: Optional[str] = None
    """Temporary directory for intermediate files. Uses system temp if None."""

    keep_intermediate: bool = False
    """Whether to keep intermediate files (triage.json, fast_pages.json, ai_pages/)."""

    @classmethod
    def fast_mode(cls) -> "HybridPipelineConfig":
        """Create a configuration optimized for speed.

        Uses higher thresholds to route more pages to fast path.
        """
        return cls(
            triage=TriageConfig(
                image_area_threshold=0.15,
                text_coverage_threshold=0.05,
                missing_to_unicode_threshold=0.50,
            ),
            ai_models=AIModelConfig(
                ocr=OCRConfig(enabled=True),
                table=TableConfig(enabled=False),
                layout=LayoutConfig(enabled=False),
            ),
            batch_size=8,
        )

    @classmethod
    def quality_mode(cls) -> "HybridPipelineConfig":
        """Create a configuration optimized for quality.

        Uses lower thresholds to route more pages to AI processing.
        """
        return cls(
            triage=TriageConfig(
                image_area_threshold=0.02,
                text_coverage_threshold=0.15,
                missing_to_unicode_threshold=0.20,
            ),
            ai_models=AIModelConfig(
                ocr=OCRConfig(enabled=True),
                table=TableConfig(enabled=True),
                layout=LayoutConfig(enabled=True),
                formula=FormulaConfig(enabled=True),
                picture=PictureConfig(enabled=True),
            ),
            batch_size=2,
        )
